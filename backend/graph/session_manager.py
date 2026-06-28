"""会话持久化管理"""
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from utils.llm_factory import create_llm
from utils.logger import get_logger

logger = get_logger("SessionManager")


class SummaryManager:
    """摘要管理器 - 管理对话压缩摘要
    
    将摘要信息结构化存储，避免正则解析文本。
    """
    
    def __init__(self):
        self.summaries: List[Dict[str, Any]] = []
        self.next_id: int = 1
    
    def add_summary(self, content: str, compressed_count: int, merged: bool = False) -> Dict[str, Any]:
        """添加新摘要
        
        Args:
            content: 摘要内容
            compressed_count: 压缩的消息数量
            merged: 是否为合并后的摘要
            
        Returns:
            新添加的摘要对象
        """
        summary = {
            "id": self.next_id,
            "content": content,
            "compressed_count": compressed_count,
            "created_at": time.time(),
            "merged": merged
        }
        self.summaries.append(summary)
        self.next_id += 1
        return summary
    
    def merge_all(self, merged_content: str) -> Dict[str, Any]:
        """合并所有摘要为一个
        
        Args:
            merged_content: 合并后的摘要内容
            
        Returns:
            合并后的摘要对象
        """
        total_count = sum(s.get("compressed_count", 0) for s in self.summaries)
        
        self.summaries = []
        
        return self.add_summary(merged_content, total_count, merged=True)
    
    def to_system_message(self) -> Optional[Dict[str, str]]:
        """转换为 system 消息格式（供 Agent 使用）
        
        Returns:
            system 消息字典，或 None（无摘要时）
        """
        if not self.summaries:
            return None
        
        parts = []
        for s in self.summaries:
            if s.get("merged"):
                parts.append(f"[历史摘要{s['id']}（合并{s['compressed_count']}轮）]\n{s['content']}")
            else:
                parts.append(f"[历史摘要{s['id']}]\n{s['content']}")
        
        return {"role": "system", "content": "\n".join(parts)}
    
    def get_context_string(self) -> str:
        """获取压缩上下文字符串（供前端显示）
        
        Returns:
            压缩上下文字符串
        """
        msg = self.to_system_message()
        return msg.get("content", "") if msg else ""
    
    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> 'SummaryManager':
        """从 efficient 数据恢复
        
        Args:
            data: efficient_data 字典
            
        Returns:
            SummaryManager 实例
        """
        manager = cls()
        manager.summaries = data.get("summaries", [])
        manager.next_id = data.get("next_summary_id", 1)
        return manager
    
    def to_data(self) -> Dict[str, Any]:
        """导出为数据字典
        
        Returns:
            包含 summaries 和 next_summary_id 的字典
        """
        return {
            "summaries": self.summaries,
            "next_summary_id": self.next_id
        }


class SessionManager:
    """会话管理器 - 管理 JSON 会话文件
    
    存储结构：
    - sessions/original/{id}.json - 原始对话记录（完整消息，用于前端显示）
    - sessions/efficient/{id}.json - 有效对话记录（压缩后，用于LLM请求）
    
    缓存机制：
    - _cache: 内存缓存，减少文件读取次数
    - _cache_hits / _cache_misses: 缓存统计，用于监控
    """
    
    def __init__(self, base_dir: Path):
        self.sessions_dir = base_dir / "sessions"
        self.original_dir = self.sessions_dir / "original"
        self.efficient_dir = self.sessions_dir / "efficient"
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        self.original_dir.mkdir(parents=True, exist_ok=True)
        self.efficient_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_original_path(self, session_id: str) -> Path:
        """获取原始对话记录路径"""
        return self.original_dir / f"{session_id}.json"
    
    def _get_efficient_path(self, session_id: str) -> Path:
        """获取有效对话记录路径"""
        return self.efficient_dir / f"{session_id}.json"
    
    def create_session(self) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())[:8]
        timestamp = time.time()
        
        # 原始对话记录
        original_data = {
            "session_id": session_id,
            "title": "",
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": []
        }
        
        efficient_data = {
            "session_id": session_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "compressed_rounds": 0,
            "last_compressed_index": -1,
            "summaries": [],
            "next_summary_id": 1,
            "messages": []
        }
        
        try:
            with open(self._get_original_path(session_id), "w", encoding="utf-8") as f:
                json.dump(original_data, f, ensure_ascii=False, indent=2)
            
            with open(self._get_efficient_path(session_id), "w", encoding="utf-8") as f:
                json.dump(efficient_data, f, ensure_ascii=False, indent=2)
            
            self._set_cache(session_id, "original", original_data)
            self._set_cache(session_id, "efficient", efficient_data)
            logger.debug(f"创建会话成功 [{session_id}]")
            return session_id
        except Exception as e:
            logger.error(f"创建会话失败 [{session_id}]: {e}")
            raise
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话（按更新时间倒序）"""
        sessions = []
        
        for path in self.original_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                sessions.append({
                    "id": path.stem,
                    "title": data.get("title", ""),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "message_count": len(data.get("messages", []))
                })
            except Exception as e:
                logger.warning(f"读取会话失败 [{path.stem}]: {e}")
        
        # 按更新时间倒序
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions
    
    def _get_from_cache(self, session_id: str, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        cache_full_key = f"{session_id}:{cache_key}"
        if cache_full_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_full_key]
        self._cache_misses += 1
        return None
    
    def _set_cache(self, session_id: str, cache_key: str, data: Dict[str, Any]):
        """设置缓存"""
        cache_full_key = f"{session_id}:{cache_key}"
        self._cache[cache_full_key] = data
    
    def _invalidate_cache(self, session_id: str):
        """清除指定会话的缓存"""
        keys_to_remove = [k for k in self._cache if k.startswith(f"{session_id}:")]
        for k in keys_to_remove:
            del self._cache[k]
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0,
            "cached_sessions": len(set(k.split(":")[0] for k in self._cache))
        }
    
    def load_original_session(self, session_id: str) -> Dict[str, Any]:
        """加载原始对话记录（用于前端显示）
        
        优先从缓存读取，缓存未命中时从文件读取并缓存。
        
        Raises:
            FileNotFoundError: 会话文件不存在
            json.JSONDecodeError: JSON解析失败
            Exception: 其他读取错误
        """
        cached = self._get_from_cache(session_id, "original")
        if cached is not None:
            return cached
        
        path = self._get_original_path(session_id)
        
        if not path.exists():
            raise FileNotFoundError(f"会话不存在: {session_id}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self._set_cache(session_id, "original", data)
        return data
    
    def load_efficient_session(self, session_id: str) -> Dict[str, Any]:
        """加载有效对话记录（用于LLM请求）
        
        优先从缓存读取，缓存未命中时从文件读取并缓存。
        
        Raises:
            FileNotFoundError: 会话文件不存在
            json.JSONDecodeError: JSON解析失败
            Exception: 其他读取错误
        """
        cached = self._get_from_cache(session_id, "efficient")
        if cached is not None:
            return cached
        
        path = self._get_efficient_path(session_id)
        
        if not path.exists():
            raise FileNotFoundError(f"会话不存在: {session_id}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self._set_cache(session_id, "efficient", data)
        return data
    
    def load_session_for_agent(self, session_id: str) -> List[Dict[str, Any]]:
        """加载会话（为 LLM 优化格式）
        
        从 summaries 生成 system 消息，合并连续的 assistant 消息。
        """
        data = self.load_efficient_session(session_id)
        messages = data.get("messages", [])
        
        summary_manager = SummaryManager.from_data(data)
        system_msg = summary_manager.to_system_message()
        
        merged = []
        current_assistant = None
        
        for msg in messages:
            if msg.get("role") == "assistant":
                if current_assistant is None:
                    current_assistant = msg
                else:
                    current_assistant["content"] = current_assistant.get("content", "") + "\n" + msg.get("content", "")
                    if "tool_calls" in msg:
                        if "tool_calls" not in current_assistant:
                            current_assistant["tool_calls"] = []
                        current_assistant["tool_calls"].extend(msg["tool_calls"])
            else:
                if current_assistant is not None:
                    merged.append(current_assistant)
                    current_assistant = None
                merged.append(msg)
        
        if current_assistant is not None:
            merged.append(current_assistant)
        
        if system_msg:
            merged.insert(0, system_msg)
        
        return merged
    
    def save_message(self, session_id: str, role: str, content: str, tool_calls: Optional[List] = None, tool_call_id: Optional[str] = None, images: Optional[List[str]] = None):
        """保存消息到会话（同时保存到 original 和 efficient）
        
        优化：使用缓存减少文件读取，保存后同步更新缓存。
        """
        message = {
            "role": role,
            "content": content
        }
        
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        
        if images:
            message["images"] = images
        
        try:
            original_data = self.load_original_session(session_id)
            original_data["messages"].append(message)
            original_data["updated_at"] = time.time()
            
            with open(self._get_original_path(session_id), "w", encoding="utf-8") as f:
                json.dump(original_data, f, ensure_ascii=False, indent=2)
            
            self._set_cache(session_id, "original", original_data)
        except Exception as e:
            logger.error(f"保存消息到original失败 [{session_id}]: {e}")
            raise
        
        try:
            efficient_data = self.load_efficient_session(session_id)
            efficient_data["messages"].append(message)
            efficient_data["updated_at"] = time.time()
            
            with open(self._get_efficient_path(session_id), "w", encoding="utf-8") as f:
                json.dump(efficient_data, f, ensure_ascii=False, indent=2)
            
            self._set_cache(session_id, "efficient", efficient_data)
            logger.debug(f"保存消息成功 [{session_id}]: role={role}")
        except Exception as e:
            logger.error(f"保存消息到efficient失败 [{session_id}]: {e}")
            raise
    
    def update_title(self, session_id: str, title: str):
        """更新会话标题（只更新 original）"""
        try:
            data = self.load_original_session(session_id)
            data["title"] = title
            data["updated_at"] = time.time()
            
            path = self._get_original_path(session_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self._set_cache(session_id, "original", data)
            logger.debug(f"更新会话标题成功 [{session_id}]: {title}")
        except Exception as e:
            logger.error(f"更新会话标题失败 [{session_id}]: {e}")
            raise
    
    def rename_session(self, session_id: str, new_title: str):
        """重命名会话"""
        self.update_title(session_id, new_title)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话（删除会话文件和对应的任务列表）"""
        self._invalidate_cache(session_id)
        
        original_path = self._get_original_path(session_id)
        efficient_path = self._get_efficient_path(session_id)

        deleted = False
        errors = []
        
        if original_path.exists():
            try:
                original_path.unlink()
                deleted = True
                logger.debug(f"删除original会话文件成功 [{session_id}]")
            except Exception as e:
                errors.append(f"original: {e}")
        
        if efficient_path.exists():
            try:
                efficient_path.unlink()
                deleted = True
                logger.debug(f"删除efficient会话文件成功 [{session_id}]")
            except Exception as e:
                errors.append(f"efficient: {e}")

        try:
            from tools.todo_tool import get_todo_file_path
            todo_path = get_todo_file_path(session_id)
            if todo_path.exists():
                todo_path.unlink()
                logger.debug(f"删除todo文件成功 [{session_id}]")
        except Exception as e:
            errors.append(f"todo: {e}")
        
        if errors:
            logger.warning(f"删除会话部分失败 [{session_id}]: {errors}")

        return deleted
    
    def get_first_user_message(self, session_id: str) -> Optional[str]:
        """获取会话中的第一条用户消息"""
        data = self.load_original_session(session_id)
        messages = data.get("messages", [])
        
        for msg in messages:
            if msg.get("role") == "user":
                return msg.get("content", "")
        
        return None
    
    def _build_conversation_text(self, messages: List[Dict[str, Any]]) -> str:
        """构建对话文本（精确角色区分）"""
        role_map = {
            "user": "用户",
            "assistant": "助手",
            "system": "系统",
            "tool": "工具"
        }
        
        conversation_text = []
        for msg in messages:
            role = role_map.get(msg.get("role"), "其他")
            content = msg.get("content", "")
            # 截取前500字符，避免过长
            if len(content) > 500:
                content = content[:500] + "..."
            conversation_text.append(f"{role}: {content}")
        
        return "\n".join(conversation_text)
    
    def _compress_summaries(self, summaries: List[str]) -> str:
        """将多个历史摘要压缩成一个更简洁的摘要（3轮合并时使用）"""
        try:
            llm = create_llm(temperature=0.3, override_params={"thinking_enabled": False})
            
            combined = "\n\n".join([f"[摘要 {i+1}]\n{s}" for i, s in enumerate(summaries)])
            
            prompt = f"""请将以下多个对话摘要合并成一个更简洁的整体摘要。
保留关键信息、重要事实和决策，去除冗余细节。

{combined}

请输出一个简洁的总结（不超过500字）："""

            response = llm.invoke(prompt)
            compressed = response.content.strip()
            
            logger.info(f"历史摘要合并完成: {len(summaries)} 轮 -> 1 轮, 长度={len(compressed)}")
            return compressed
            
        except Exception as e:
            logger.error(f"摘要合并失败: {e}")
            # 失败时简单合并
            fallback = "\n\n".join([f"[历史 {i+1}] {s[:200]}..." for i, s in enumerate(summaries)])
            logger.warning(f"使用简单合并作为fallback: {len(fallback)} 字符")
            return fallback
    
    def prepare_compression(self, session_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
        """准备压缩数据，返回待压缩消息、efficient数据和云端请求详情
        
        Returns:
            (待压缩消息列表, efficient数据, 云端请求详情JSON字符串)
        """
        original_data = self.load_original_session(session_id)
        efficient_data = self.load_efficient_session(session_id)
        
        original_messages = original_data.get("messages", [])
        last_compressed_index = efficient_data.get("last_compressed_index", -1)
        
        # 获取新增消息（从上次压缩的索引之后）
        new_messages = original_messages[last_compressed_index + 1:]
        
        if not new_messages:
            return [], efficient_data, ""
        
        # 构建对话文本
        conversation_text = self._build_conversation_text(new_messages)
        
        # 构建云端请求详情
        request_detail = {
            "model": "compression-model",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个对话摘要助手，请对对话进行摘要。"
                },
                {
                    "role": "user",
                    "content": f"""请对以下对话进行摘要，总结主要讨论内容和关键信息。
摘要要求：
- 不超过1000字
- 使用中文
- 保留关键事实和决定

对话内容：
{conversation_text}

摘要："""
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }
        
        return new_messages, efficient_data, json.dumps(request_detail, ensure_ascii=False, indent=2)
    
    def execute_compression(self, session_id: str, summary: str, new_messages: List[Dict[str, Any]], efficient_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行压缩操作（重构版）
        
        使用 SummaryManager 管理摘要，避免正则解析。
        
        Args:
            session_id: 会话ID
            summary: LLM生成的摘要
            new_messages: 本次压缩的新增消息列表（来自 original）
            efficient_data: 当前的efficient数据
            
        Returns:
            压缩结果信息
        """
        last_compressed_index = efficient_data.get("last_compressed_index", -1)
        compressed_rounds = efficient_data.get("compressed_rounds", 0) + 1
        new_last_index = last_compressed_index + len(new_messages)
        
        summary_manager = SummaryManager.from_data(efficient_data)
        
        merged = False
        merged_rounds = None
        
        if compressed_rounds >= 3 and compressed_rounds % 3 == 0 and summary_manager.summaries:
            all_contents = [s.get("content", "") for s in summary_manager.summaries] + [summary]
            merged_content = self._compress_summaries(all_contents)
            summary_manager.merge_all(merged_content)
            compressed_rounds = 0
            merged = True
            merged_rounds = len(all_contents)
        else:
            summary_manager.add_summary(summary, len(new_messages))
        
        efficient_messages = efficient_data.get("messages", [])
        non_system_messages = [m for m in efficient_messages if m.get("role") != "system"]
        
        keep_from_index = new_last_index - last_compressed_index
        if keep_from_index < len(non_system_messages):
            uncompressed_messages = non_system_messages[keep_from_index:]
        else:
            uncompressed_messages = []
        
        efficient_data.update({
            "compressed_rounds": compressed_rounds,
            "last_compressed_index": new_last_index,
            "summaries": summary_manager.summaries,
            "next_summary_id": summary_manager.next_id,
            "messages": uncompressed_messages,
            "updated_at": time.time()
        })
        
        try:
            with open(self._get_efficient_path(session_id), "w", encoding="utf-8") as f:
                json.dump(efficient_data, f, ensure_ascii=False, indent=2)
            
            self._set_cache(session_id, "efficient", efficient_data)
            logger.info(f"对话压缩完成 [{session_id}]: 压缩{len(new_messages)}条消息, "
                       f"新索引={new_last_index}, 轮数={compressed_rounds}, 合并={merged}")
        except Exception as e:
            logger.error(f"保存压缩后的efficient文件失败 [{session_id}]: {e}")
            raise
        
        return {
            "compressed_count": len(new_messages),
            "new_last_index": new_last_index,
            "compressed_rounds": compressed_rounds,
            "merged": merged,
            "merged_rounds": merged_rounds
        }
