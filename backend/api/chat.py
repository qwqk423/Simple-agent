"""聊天 API - SSE 流式对话"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph.agent import agent_manager
from graph.title_generator import title_generator
from utils.logger import get_logger

logger = get_logger("ChatAPI")


router = APIRouter()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: str
    images: list[str] = []  # base64 图片列表
    stream: bool = True


@router.post("/chat")
async def chat(request: ChatRequest):
    """SSE 流式聊天接口"""
    
    # 验证会话是否存在
    try:
        session_data = agent_manager.session_manager.load_original_session(request.session_id)
    except FileNotFoundError:
        logger.warning(f"会话不存在: {request.session_id}")
        raise HTTPException(status_code=404, detail="会话不存在")
    except Exception as e:
        logger.error(f"加载会话失败 [{request.session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"加载会话失败: {str(e)}")
    
    # 检查是否是首次消息（用于生成标题）
    is_first_message = len(session_data.get("messages", [])) == 0
    
    # 获取优化后的历史记录
    try:
        history = agent_manager.session_manager.load_session_for_agent(request.session_id)
    except Exception as e:
        logger.error(f"加载会话历史失败 [{request.session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"加载会话历史失败: {str(e)}")
    
    logger.info(f"开始处理聊天请求 [{request.session_id}]: 消息长度={len(request.message)}, 图片数={len(request.images)}")
    
    async def event_generator():
        """SSE 事件生成器"""
        assistant_contents = []
        current_content = ""
        tool_calls = []
        error_occurred = False
        title_generated = False
        user_message_saved = False
        
        def save_callback(role: str, content: str, **kwargs):
            """实时保存回调函数 - 用于保存工具调用和结果"""
            try:
                if role == "assistant" and kwargs.get("tool_calls"):
                    # 保存助手消息（包含 tool_calls）
                    agent_manager.session_manager.save_message(
                        request.session_id,
                        "assistant",
                        content,
                        tool_calls=kwargs.get("tool_calls")
                    )
                    logger.debug(f"保存助手消息（含tool_calls）[{request.session_id}]")
                elif role == "tool":
                    # 保存工具结果消息
                    agent_manager.session_manager.save_message(
                        request.session_id,
                        "tool",
                        content,
                        tool_call_id=kwargs.get("tool_call_id")
                    )
                    logger.debug(f"保存工具结果 [{request.session_id}]: tool_call_id={kwargs.get('tool_call_id')}")
            except Exception as e:
                logger.error(f"实时保存失败 [{request.session_id}]: {e}")
        
        def save_conversation():
            """保存最终对话到会话历史（只保存最终的 assistant 回复）"""
            nonlocal assistant_contents, current_content
            
            # 合并所有内容
            all_contents = assistant_contents.copy()
            if current_content:
                all_contents.append(current_content)
            
            # 如果没有内容，不保存（避免覆盖之前的 tool_calls 消息）
            if not all_contents:
                logger.debug(f"无内容需要保存 [{request.session_id}]")
                return None
            
            final_content = "\n".join(all_contents).strip()
            
            # 如果最终内容为空，不保存（之前的 tool_start 已保存过带 tool_calls 的消息）
            if not final_content:
                logger.debug(f"最终内容为空，跳过保存 [{request.session_id}]")
                return None
            
            # 保存最终的助手消息（不包含 tool_calls，因为已经单独保存过了）
            try:
                agent_manager.session_manager.save_message(
                    request.session_id,
                    "assistant",
                    final_content
                )
                logger.debug(f"保存助手最终回复成功 [{request.session_id}]: 长度={len(final_content)}")
            except Exception as e:
                logger.error(f"保存助手最终回复失败 [{request.session_id}]: {e}")
                raise
            
            # 生成标题（仅首次消息）
            if is_first_message:
                # 返回消息作为备用标题
                fallback = request.message[:20] if request.message else "新对话"
                logger.debug(f"准备备用标题 [{request.session_id}]: {fallback}")
                return fallback
            
            return None
        
        try:
            # 先保存用户消息（只执行一次）
            if not user_message_saved:
                try:
                    agent_manager.session_manager.save_message(
                        request.session_id,
                        "user",
                        request.message,
                        images=request.images if request.images else None
                    )
                    user_message_saved = True
                    logger.debug(f"保存用户消息成功 [{request.session_id}]")
                except Exception as e:
                    logger.error(f"保存用户消息失败 [{request.session_id}]: {e}")
                    raise
            
            # 调试：打印请求信息
            logger.debug(f"请求详情 [{request.session_id}]: 消息长度={len(request.message)}, 图片数={len(request.images)}")
            
            # 流式生成回复
            try:
                stream_iter = agent_manager.astream(
                    message=request.message,
                    session_id=request.session_id,
                    history=history,
                    images=request.images,
                    save_callback=save_callback
                )
            except Exception as e:
                logger.error(f"初始化流式生成失败 [{request.session_id}]: {e}")
                raise
            
            async for event in stream_iter:
                try:
                    event_type = event.get("type")
                    event_data = event.get("data", {})
                    
                    # 调试：记录 todo_update 事件
                    if event_type == "todo_update":
                        logger.debug(f"发送 todo_update 事件 [{request.session_id}]: {event_data}")
                    
                    # 发送 SSE 事件
                    try:
                        yield f"event: {event_type}\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    except (BrokenPipeError, ConnectionResetError):
                        logger.warning(f"客户端断开连接 [{request.session_id}]")
                        return
                    except Exception as e:
                        logger.error(f"发送 SSE 事件失败 [{request.session_id}]: {e}")
                        raise
                    
                    # 收集助手回复
                    if event_type == "token":
                        current_content += event_data.get("content", "")
                    elif event_type == "tool_start":
                        # 工具调用前保存已生成的内容
                        if current_content:
                            assistant_contents.append(current_content)
                            current_content = ""
                        # 记录工具调用
                        tool_call_info = {
                            "id": event_data.get("id", f"call_{len(tool_calls)+1}"),
                            "tool": event_data.get("tool", ""),
                            "input": event_data.get("input", {}),
                            "output": "",  # 空表示执行中
                        }
                        tool_calls.append(tool_call_info)
                        logger.debug(f"工具调用开始 [{request.session_id}]: {tool_call_info['tool']}")
                    elif event_type == "tool_end":
                        # 通过 ID 精确匹配工具调用
                        tool_id = event_data.get("id", "")
                        tool_name = event_data.get("tool", "")
                        matched = False
                        for tc in tool_calls:
                            if tc["id"] == tool_id and not tc["output"]:
                                tc["output"] = event_data.get("output", "")
                                tc["status"] = event_data.get("status", "success")
                                matched = True
                                break
                        # 如果 ID 匹配失败，退回到名称匹配（兼容模式）
                        if not matched:
                            for tc in reversed(tool_calls):
                                if tc["tool"] == tool_name and not tc["output"]:
                                    tc["output"] = event_data.get("output", "")
                                    tc["status"] = event_data.get("status", "success")
                                    break
                        status = event_data.get("status", "success")
                        if status != "success":
                            logger.warning(f"工具调用失败 [{request.session_id}]: {tool_name}, 状态={status}")
                        else:
                            logger.debug(f"工具调用完成 [{request.session_id}]: {tool_name}")
                    elif event_type == "done":
                        # 保存最后一段回复
                        if current_content:
                            assistant_contents.append(current_content)
                            current_content = ""
                        
                        # 准备备用标题（在保存前准备，确保即使保存失败也有备用标题）
                        fallback_title = None
                        if is_first_message and not title_generated:
                            fallback_title = request.message[:20] if request.message else "新对话"
                        
                        # 保存消息到会话
                        save_success = False
                        try:
                            save_result = save_conversation()
                            # 如果 save_conversation 返回了标题，使用它作为备用标题
                            if save_result:
                                fallback_title = save_result
                            save_success = True
                            
                            # 清空已保存的内容，防止 finally 块重复保存
                            assistant_contents = []
                        except Exception as e:
                            logger.error(f"保存会话失败 [{request.session_id}]: {e}")
                            error_occurred = True
                            try:
                                yield f"event: error\ndata: {json.dumps({'error': f'保存会话失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                            except (BrokenPipeError, ConnectionResetError):
                                logger.warning(f"发送错误事件时客户端断开 [{request.session_id}]")
                                return
                        
                        # 首次消息生成标题（异步）- 独立于保存逻辑，确保即使保存失败也会尝试生成
                        if is_first_message and not title_generated:
                            title_generated = True
                            title = None
                            try:
                                title = await title_generator.generate(request.message)
                                agent_manager.session_manager.update_title(request.session_id, title)
                                logger.info(f"标题生成成功 [{request.session_id}]: {title}")
                            except Exception as e:
                                title = fallback_title or "新对话"
                                logger.error(f"标题生成失败 [{request.session_id}]: {e}, 使用备用标题: {title}")
                            
                            try:
                                yield f"event: title\ndata: {json.dumps({'session_id': request.session_id, 'title': title}, ensure_ascii=False)}\n\n"
                            except (BrokenPipeError, ConnectionResetError):
                                logger.warning(f"发送标题事件时客户端断开 [{request.session_id}]")
                                return
                        
                except Exception as e:
                    # 处理单个事件的处理错误，不影响整体流程
                    logger.error(f"事件处理错误 [{request.session_id}]: {e}")
                    error_occurred = True
                    try:
                        yield f"event: error\ndata: {json.dumps({'error': f'事件处理错误: {str(e)}'}, ensure_ascii=False)}\n\n"
                    except (BrokenPipeError, ConnectionResetError):
                        logger.warning(f"发送错误事件时客户端断开 [{request.session_id}]")
                        return
                    
        except Exception as e:
            # 处理主要的流式生成错误
            logger.error(f"流式生成错误 [{request.session_id}]: {e}")
            error_occurred = True
            try:
                yield f"event: error\ndata: {json.dumps({'error': f'生成回复时出错: {str(e)}'}, ensure_ascii=False)}\n\n"
            except (BrokenPipeError, ConnectionResetError):
                logger.warning(f"发送错误事件时客户端断开 [{request.session_id}]")
                return
        finally:
            # 确保保存已生成的内容（即使发生错误）
            if current_content and not error_occurred:
                assistant_contents.append(current_content)
            
            # 如果有内容生成但未保存，尝试保存
            if assistant_contents and not error_occurred:
                try:
                    save_conversation()
                    logger.info(f"对话完成并保存 [{request.session_id}]")
                except Exception as e:
                    logger.error(f"最终保存失败 [{request.session_id}]: {e}")
                    try:
                        yield f"event: error\ndata: {json.dumps({'error': f'保存会话失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                    except (BrokenPipeError, ConnectionResetError):
                        logger.warning(f"发送错误事件时客户端断开 [{request.session_id}]")
                        return
            
            # 确保发送 done 事件
            try:
                yield f"event: done\ndata: {json.dumps({'session_id': request.session_id}, ensure_ascii=False)}\n\n"
            except (BrokenPipeError, ConnectionResetError):
                logger.warning(f"发送done事件时客户端断开 [{request.session_id}]")
            except Exception as e:
                logger.error(f"发送done事件失败 [{request.session_id}]: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/chat/last-request")
async def get_last_request():
    """获取最后一次发送给 LLM 的完整请求内容"""
    try:
        if not agent_manager.last_request:
            logger.debug("暂无请求记录")
            return {
                "success": False,
                "message": "暂无请求记录",
                "request": None
            }
        
        logger.debug("获取最后一次请求记录")
        return {
            "success": True,
            "request": agent_manager.last_request
        }
    except Exception as e:
        logger.error(f"获取最后请求记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取请求记录失败: {str(e)}")
