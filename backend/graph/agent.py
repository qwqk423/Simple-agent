"""Agent 管理器 - 核心 Agent 逻辑"""
import json
import time
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List, Optional

from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage, ToolMessage,
)
from langchain_core.messages.utils import convert_to_openai_messages

from config import settings, get_config_manager
from tools import get_all_tools
from tools.todo_tool import set_current_session_id
from .session_manager import SessionManager
from .prompt_builder import PromptBuilder
from .memory_indexer import get_memory_indexer
from utils.llm_factory import create_llm
from utils.logger import get_logger

logger = get_logger("Agent")


class AgentManager:
    """Agent 管理器 - 管理 LLM、工具和会话"""
    
    def __init__(self):
        self.base_dir: Optional[Path] = None
        self.tools: List = []
        self.session_manager: Optional[SessionManager] = None
        self.prompt_builder: Optional[PromptBuilder] = None
        self.memory_indexer = None
        self.last_request: Optional[Dict[str, Any]] = None  # 记录最后一次发送给 LLM 的请求
    
    def initialize(self, base_dir: Path):
        """初始化 Agent 管理器"""
        self.base_dir = base_dir
        
        # 加载工具
        try:
            self.tools = get_all_tools(base_dir)
            logger.info(f"加载了 {len(self.tools)} 个工具: {[t.name for t in self.tools]}")
        except Exception as e:
            logger.error(f"加载工具失败: {e}")
            raise
        
        # 初始化会话管理器
        try:
            self.session_manager = SessionManager(base_dir)
            logger.debug("会话管理器初始化完成")
        except Exception as e:
            logger.error(f"初始化会话管理器失败: {e}")
            raise
        
        # 初始化 Prompt 构建器
        try:
            self.prompt_builder = PromptBuilder(base_dir)
            logger.debug("Prompt构建器初始化完成")
        except Exception as e:
            logger.error(f"初始化Prompt构建器失败: {e}")
            raise
        
        # 初始化记忆索引器
        try:
            self.memory_indexer = get_memory_indexer(base_dir)
            logger.debug("记忆索引器初始化完成")
        except Exception as e:
            logger.error(f"初始化记忆索引器失败: {e}")
            raise
        
        logger.info("Agent管理器初始化完成")

    def _get_config_and_prompt(self) -> tuple[dict, str]:
        """
        获取配置参数和 System Prompt
        
        Returns:
            (params, system_prompt): 配置参数字典和系统提示词
        """
        config_manager = get_config_manager()
        params = config_manager.llm_params if config_manager else {}
        rag_mode = config_manager.rag_mode if config_manager else False
        thinking_enabled = params.get("thinking_enabled", True)
        system_prompt = self.prompt_builder.build_system_prompt(
            rag_mode=rag_mode, 
            thinking_enabled=thinking_enabled
        )
        return params, system_prompt
    
    async def astream(
        self,
        message: str,
        session_id: str,
        history: List[Dict[str, Any]],
        images: List[str] = None,
        save_callback: Optional[callable] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式执行 Agent
        
        事件类型:
        - retrieval: RAG 检索结果
        - token: LLM 输出 token
        - tool_start: 工具调用开始
        - tool_end: 工具调用结束
        - done: 完成
        
        使用原生 OpenAI 客户端以支持 Qwen 的 reasoning_content
        
        Args:
            save_callback: 可选的保存回调函数，用于实时保存消息到会话
                          函数签名: save_callback(role, content, **kwargs)
        """
        try:
            # 设置当前会话ID（供工具使用）
            set_current_session_id(session_id)
            
            # RAG 检索（如果开启）
            rag_context = ""
            config_manager = get_config_manager()
            if config_manager and config_manager.rag_mode:
                try:
                    query = message
                    retrieval_results = self.memory_indexer.retrieve(query, top_k=3)
                    
                    if retrieval_results:
                        logger.debug(f"RAG检索到 {len(retrieval_results)} 条结果 [{session_id}]")
                        yield {
                            "type": "retrieval",
                            "data": {
                                "query": query,
                                "results": retrieval_results
                            }
                        }
                        
                        # 构建 RAG 上下文
                        rag_parts = ["[记忆检索结果]"]
                        for i, r in enumerate(retrieval_results, 1):
                            rag_parts.append(f"[{i}] {r['text']}")
                        rag_context = "\n".join(rag_parts)
                except Exception as e:
                    logger.warning(f"RAG检索失败 [{session_id}]: {e}")
            
            # 获取配置参数和 System Prompt
            params, system_prompt = self._get_config_and_prompt()
            
            # 构建消息
            messages = []
            
            # 处理历史消息中的 system 消息（压缩摘要）
            compressed_summary = ""
            history_without_system = []
            
            for msg in history:
                if msg.get("role") == "system":
                    # 提取压缩摘要
                    compressed_summary = msg.get("content", "")
                else:
                    history_without_system.append(msg)
            
            # 构建完整的 system 消息
            if compressed_summary:
                combined_system = f"{system_prompt}\n\n[历史对话摘要]\n{compressed_summary}"
                messages.append(SystemMessage(content=combined_system))
            else:
                messages.append(SystemMessage(content=system_prompt))
            
            # 历史消息（排除 system 消息）
            # 先处理一遍，收集有效的 tool_call_id
            valid_tool_call_ids = set()
            processed_history = []
            
            for msg in history_without_system:
                role = msg.get("role")
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls", [])
                tool_call_id = msg.get("tool_call_id", "")
                msg_images = msg.get("images", [])
                
                if role == "user":
                    processed_history.append(msg)
                elif role == "assistant":
                    # 过滤无效的 tool_calls
                    if tool_calls:
                        valid_tool_calls = [
                            tc for tc in tool_calls
                            if tc.get("function", {}).get("name")
                        ]
                        if valid_tool_calls:
                            # 收集有效的 tool_call_id
                            for tc in valid_tool_calls:
                                if tc.get("id"):
                                    valid_tool_call_ids.add(tc["id"])
                            msg["tool_calls"] = valid_tool_calls
                        else:
                            msg.pop("tool_calls", None)
                    # 只有在有内容或有有效工具调用时才保留
                    if content or msg.get("tool_calls"):
                        processed_history.append(msg)
                elif role == "tool":
                    # 只保留与有效 tool_calls 对应的 tool 消息
                    if tool_call_id and tool_call_id in valid_tool_call_ids:
                        processed_history.append(msg)
            
            # 构建最终消息列表
            for msg in processed_history:
                role = msg.get("role")
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls", [])
                tool_call_id = msg.get("tool_call_id", "")
                msg_images = msg.get("images", [])

                if role == "user":
                    # 用户消息：支持多模态（文字+图片）
                    if msg_images and len(msg_images) > 0:
                        # 多模态格式
                        msg_content = [{"type": "text", "text": content or ""}]
                        for img_base64 in msg_images:
                            msg_content.append({
                                "type": "image_url",
                                "image_url": {"url": img_base64}
                            })
                        messages.append(HumanMessage(content=msg_content))
                    else:
                        messages.append(HumanMessage(content=content or ""))
                elif role == "assistant":
                    # Assistant 消息
                    if tool_calls:
                        # 转换为 langchain ToolCall 格式（name/args 而非 function.name/function.arguments）
                        lc_tool_calls = []
                        for tc in tool_calls:
                            fn = tc.get("function", {})
                            args_str = fn.get("arguments", "{}")
                            try:
                                args = json.loads(args_str) if args_str else {}
                            except json.JSONDecodeError:
                                args = {"_raw": args_str}
                            lc_tool_calls.append({
                                "id": tc.get("id", ""),
                                "name": fn.get("name", ""),
                                "args": args,
                            })
                        messages.append(AIMessage(content=content or "", tool_calls=lc_tool_calls))
                    else:
                        messages.append(AIMessage(content=content or ""))
                elif role == "tool":
                    # 工具消息
                    messages.append(ToolMessage(content=content or "", tool_call_id=tool_call_id))
            
            # 当前用户消息（支持多模态）
            input_text = message
            if rag_context:
                input_text = f"{rag_context}\n\n用户问题: {message}"
            
            # 调试：打印图片信息
            logger.debug(f"当前消息图片数量 [{session_id}]: {len(images) if images else 0}")
            
            # 构建用户消息内容
            if images:
                # 多模态消息格式
                content = [{"type": "text", "text": input_text}]
                for img_base64 in images:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": img_base64}
                    })
                messages.append(HumanMessage(content=content))
            else:
                messages.append(HumanMessage(content=input_text))
            
            # 从 config_manager 获取当前模型配置（保留用于 last_request 记录）
            current_model = None
            config_manager = get_config_manager()
            if config_manager:
                current_model = config_manager.get_current_model("llm")
                logger.debug(f"从 config_manager 获取模型: {current_model}")

            # 如果没有获取到，使用 settings 作为回退
            if not current_model:
                logger.warning("config_manager 未返回模型配置，使用 settings 作为回退")
                current_model = {
                    "model": settings.llm_model,
                    "api_key": settings.openai_api_key,
                    "base_url": settings.openai_base_url,
                }

            # 创建 LLM 实例（复用 llm_factory；思考模式由 extra_body.enable_thinking 控制）
            try:
                llm = create_llm(
                    streaming=True,
                    model_id=current_model.get("id") if config_manager else None,
                )
                # ponytail: 预构建 openai tools 格式（langchain bind_tools 内部转换），循环内复用
                tools_payload = llm.bind_tools(self.tools).kwargs.get('tools') if self.tools else None
            except Exception as e:
                logger.error(f"创建LLM实例失败: {e}")
                raise

            logger.debug(f"调用LLM [{session_id}]: model={current_model['model']}")
            
            # 思考模式开关：Qwen3 通过 extra_body.enable_thinking 控制
            thinking_enabled = params.get("thinking_enabled", True)

            # 记录发送给 LLM 的完整请求
            # ponytail: 记录实际发给 openai 的请求（转换后 messages + openai tools 格式），前端直接展示
            self.last_request = {
                "model": current_model["model"],
                "messages": convert_to_openai_messages(messages),
                "tools": tools_payload,
                "thinking_enabled": thinking_enabled,
                "timestamp": time.time(),
            }
            
            # REPL 循环：直到调用 finish 或达到最大循环次数
            max_iterations = 50  # 防止无限循环
            iteration = 0
            session_finished = False
            final_response = ""
            
            while iteration < max_iterations and not session_finished:
                iteration += 1
                logger.debug(f"循环迭代 [{session_id}]: {iteration}/{max_iterations}")
                
                # 调用 LLM（带工具）
                full_response = ""
                full_thinking = ""
                tool_calls_data = {}  # ponytail: 按 tc.index 累积，支持并发多 tool_calls
                
                try:
                    # ponytail: langchain ChatOpenAI 1.3.2 不提取 reasoning_content（base.py:5-11 注释明确），
                    # 改用底层 openai SDK 直接流式，拿 delta.reasoning_content
                    # 保留 langchain messages 类型 + bind_tools 构建 tools（P2-A 成果）
                    openai_messages = convert_to_openai_messages(messages)
                    request_params = dict(llm._default_params)
                    request_params.update({
                        "messages": openai_messages,
                        "stream": True,
                    })
                    if tools_payload:
                        request_params["tools"] = tools_payload
                    stream = await llm.async_client.create(**request_params)
                except Exception as e:
                    logger.error(f"调用LLM失败 [{session_id}]: {e}")
                    raise

                # ponytail: tool_calls_data 改为 dict by index 累积
                # OpenAI 流式协议：tc.index 是稳定标识，tc.id 只在首 chunk 出现

                async for chunk in stream:
                    try:
                        # chunk 是 openai SDK ChatCompletionChunk
                        # chunk.choices[0].delta: .content / .reasoning_content / .reasoning / .tool_calls
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta

                        # 处理思考内容 (reasoning_content)
                        # ponytail: 兼容 DashScope reasoning_content 与 vLLM reasoning 两种字段名
                        reasoning_content = getattr(delta, 'reasoning_content', None) or getattr(delta, 'reasoning', None)
                        if reasoning_content:
                            thinking_chunk = reasoning_content
                            full_thinking += thinking_chunk
                            # 发送思考内容作为特殊的 token
                            yield {
                                "type": "token",
                                "data": {
                                    "content": "",
                                    "thinking": thinking_chunk,
                                    "raw_thinking": full_thinking
                                }
                            }

                        # 处理普通内容
                        content = delta.content
                        if content:
                            content_chunk = content
                            full_response += content_chunk
                            yield {
                                "type": "token",
                                "data": {
                                    "content": content_chunk,
                                    "raw": full_response
                                }
                            }

                        # 处理工具调用：按 tc.index 累积
                        # ponytail: openai SDK 返回对象，统一转 dict 处理（兼容对象+dict）
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                if not isinstance(tc, dict):
                                    tc = tc.model_dump() if hasattr(tc, 'model_dump') else vars(tc)
                                idx = tc.get('index') if tc.get('index') is not None else 0
                                if idx not in tool_calls_data:
                                    tool_calls_data[idx] = {
                                        "id": tc.get('id') or "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    }
                                else:
                                    if tc.get('id') and not tool_calls_data[idx]["id"]:
                                        tool_calls_data[idx]["id"] = tc.get('id')
                                fn = tc.get('function') or {}
                                if fn.get('name'):
                                    tool_calls_data[idx]["function"]["name"] = fn.get('name')
                                if fn.get('arguments'):
                                    tool_calls_data[idx]["function"]["arguments"] += fn.get('arguments')
                    except Exception as e:
                        logger.warning(f"处理LLM流式响应块失败 [{session_id}]: {e}")
                        continue

                # 按 index 顺序转为 list
                tool_calls_data = [tool_calls_data[k] for k in sorted(tool_calls_data.keys())]
                
                # 如果没有工具调用，说明 LLM 直接回复了（文本形式）
                # 纯文本回复视为任务完成，直接结束，不再要求显式调用 finish
                if not tool_calls_data:
                    logger.debug(f"LLM直接回复，自动结束会话 [{session_id}]")
                    final_response = full_response
                    session_finished = True
                    break
                
                # 过滤不完整的工具调用（等待完整信息）
                valid_tool_calls = []
                incomplete_calls = []
                for tc in tool_calls_data:
                    tool_name = tc["function"]["name"]
                    tool_args = tc["function"]["arguments"]
                    if tool_name and tool_args:
                        valid_tool_calls.append(tc)
                    else:
                        incomplete_calls.append(tc)
                        logger.warning(f"工具调用不完整 [{session_id}]: name={tool_name}, args={tool_args}")
                
                # 如果有不完整的工具调用，提示 LLM 重新发送
                if incomplete_calls:
                    messages.append(SystemMessage(content="工具调用信息不完整，请重新调用工具并确保提供完整的工具名称和参数。"))
                    continue  # 继续循环，让 LLM 重新发送
                
                tool_calls_data = valid_tool_calls
                
                # 执行工具
                finish_called = False
                for tc in tool_calls_data:
                    tool_name = tc["function"]["name"]
                    
                    try:
                        tool_input = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError as e:
                        logger.warning(f"工具参数JSON解析失败 [{session_id}] [{tool_name}]: {e}, 尝试修复")
                        # 解析失败时，根据工具类型提供合理的默认值
                        tool_input = tc["function"]["arguments"]
                        # 如果参数是字符串且看起来像JSON但解析失败，尝试清理后再次解析
                        if isinstance(tool_input, str):
                            try:
                                # 尝试修复常见的JSON格式问题（如单引号、尾随逗号等）
                                cleaned = tool_input.replace("'", '"').replace(',}', '}').replace(',]', ']')
                                tool_input = json.loads(cleaned)
                            except json.JSONDecodeError:
                                # 仍然失败，根据工具类型提供默认结构
                                if tool_name in ["todo_write"]:
                                    tool_input = {"todos": []}
                                elif tool_name in ["terminal", "python_repl", "read_file", "fetch_url"]:
                                    tool_input = {"input": tool_input} if tool_input else {}
                                elif tool_name == "finish":
                                    tool_input = {"summary": str(tool_input) if tool_input else "任务完成"}
                                else:
                                    tool_input = {"input": tool_input} if tool_input else {}
                    
                    # 发送工具开始事件
                    yield {
                        "type": "tool_start",
                        "data": {
                            "id": tc["id"],
                            "tool": tool_name,
                            "input": tool_input
                        }
                    }
                    
                    # 实时保存助手消息（包含 tool_calls）
                    if save_callback:
                        try:
                            save_callback(
                                role="assistant",
                                content="",
                                tool_calls=[{
                                    "id": tc["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": tc["function"]["arguments"]
                                    }
                                }]
                            )
                        except Exception as e:
                            logger.error(f"保存tool_calls失败 [{session_id}]: {e}")
                    
                    # 执行工具
                    tool_result = ""
                    logger.debug(f"执行工具 [{session_id}]: {tool_name}, 输入: {tool_input}")
                    tool_found = False
                    for tool in self.tools:
                        if tool.name == tool_name:
                            tool_found = True
                            try:
                                # ponytail: async 上下文必须用 arun，避免阻塞事件循环
                                tool_result = await tool.arun(tool_input)
                                logger.debug(f"工具执行完成 [{session_id}]: {tool_name}")
                            except Exception as e:
                                tool_result = f"[错误] 工具执行失败: {str(e)}"
                                logger.error(f"工具执行失败 [{session_id}] [{tool_name}]: {e}")
                            break
                    
                    if not tool_found:
                        tool_result = f"[错误] 未知工具: {tool_name}"
                        logger.warning(f"未知工具 [{session_id}]: {tool_name}")
                    
                    # 检查是否是 finish 工具
                    if tool_name == "finish":
                        finish_called = True
                        final_response = tool_result
                        session_finished = True
                    
                    # 发送工具结束事件
                    yield {
                        "type": "tool_end",
                        "data": {
                            "id": tc["id"],
                            "tool": tool_name,
                            "output": str(tool_result)[:5000],
                            "status": "success"
                        }
                    }
                    
                    # 如果是 todo_write 工具，发送 todo_update 事件
                    if tool_name == "todo_write":
                        logger.debug(f"检测到todo_write工具，准备发送todo_update事件 [{session_id}]")
                        try:
                            # 解析工具结果中的待办事项数据
                            if isinstance(tool_input, dict) and "todos" in tool_input:
                                todos_data = tool_input["todos"]
                                # 如果 todos 是字符串，解析为数组
                                if isinstance(todos_data, str):
                                    todos_data = json.loads(todos_data)
                                logger.debug(f"发送todo_update事件 [{session_id}], todos数量: {len(todos_data)}")
                                yield {
                                    "type": "todo_update",
                                    "data": {
                                        "todos": todos_data
                                    }
                                }
                            else:
                                logger.debug(f"todo_write输入中没有todos数据 [{session_id}]")
                        except Exception as e:
                            logger.error(f"发送todo_update事件失败 [{session_id}]: {e}")
                    
                    # 实时保存工具结果消息
                    if save_callback:
                        try:
                            save_callback(
                                role="tool",
                                content=str(tool_result),
                                tool_call_id=tc["id"]
                            )
                        except Exception as e:
                            logger.error(f"保存tool结果失败 [{session_id}]: {e}")
                    
                    # 添加工具调用到消息历史（用于后续 API 调用）
                    # tc 是 OpenAI 格式 dict，转换为 langchain AIMessage.tool_calls（name/args）
                    try:
                        tc_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    except json.JSONDecodeError:
                        tc_args = {}
                    messages.append(AIMessage(
                        content="",
                        tool_calls=[{
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "args": tc_args,
                        }]
                    ))
                    messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))
                
                # 如果调用了 finish，结束循环
                if finish_called:
                    logger.debug(f"finish工具被调用，结束会话 [{session_id}]")
                    break
            
            # 检查是否达到最大循环次数
            if iteration >= max_iterations and not session_finished:
                logger.warning(f"达到最大循环次数 {max_iterations}，强制结束 [{session_id}]")
                final_response = "[警告] 达到最大执行次数限制，会话被强制结束。请简化任务或分批处理。"
            
            # 完成
            logger.info(f"Agent执行完成 [{session_id}]: {iteration} 轮迭代")
            yield {
                "type": "done",
                "data": {
                    "content": final_response,
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Agent执行错误 [{session_id}]: {e}")
            import traceback
            logger.debug(f"异常堆栈 [{session_id}]: {traceback.format_exc()}")
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }


# 全局 Agent 管理器
agent_manager = AgentManager()
