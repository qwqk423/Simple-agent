"""会话管理 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from graph.agent import agent_manager
from graph.title_generator import title_generator
from utils.logger import get_logger

logger = get_logger("SessionsAPI")

router = APIRouter()


class RenameRequest(BaseModel):
    """重命名请求"""
    title: str


@router.get("/sessions")
async def list_sessions():
    """获取所有会话列表"""
    try:
        sessions = agent_manager.session_manager.list_sessions()
        logger.debug(f"获取会话列表: {len(sessions)} 个会话")
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.post("/sessions")
async def create_session():
    """创建新会话"""
    try:
        session_id = agent_manager.session_manager.create_session()
        logger.info(f"创建新会话成功: {session_id}")
        return {"id": session_id, "title": "", "message_count": 0}
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.put("/sessions/{session_id}")
async def rename_session(session_id: str, request: RenameRequest):
    """重命名会话"""
    try:
        agent_manager.session_manager.rename_session(session_id, request.title)
        logger.info(f"重命名会话 [{session_id}]: {request.title}")
        return {"id": session_id, "title": request.title}
    except FileNotFoundError:
        logger.warning(f"重命名失败，会话不存在: {session_id}")
        raise HTTPException(status_code=404, detail="会话不存在")
    except Exception as e:
        logger.error(f"重命名会话失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"重命名会话失败: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        success = agent_manager.session_manager.delete_session(session_id)
        if not success:
            logger.warning(f"删除会话失败，会话不存在: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"删除会话成功: {session_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """获取完整消息（含 System Prompt）- 用于 LLM 请求"""
    from graph.prompt_builder import PromptBuilder
    
    try:
        # 加载有效对话记录（包含压缩后的system消息）
        efficient_data = agent_manager.session_manager.load_efficient_session(session_id)
    except FileNotFoundError:
        logger.warning(f"获取消息失败，会话不存在: {session_id}")
        raise HTTPException(status_code=404, detail="会话不存在")
    except Exception as e:
        logger.error(f"加载有效会话失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"加载会话失败: {str(e)}")
    
    # 构建 System Prompt
    try:
        prompt_builder = PromptBuilder(agent_manager.base_dir)
        system_prompt = prompt_builder.build_system_prompt()
    except Exception as e:
        logger.error(f"构建系统提示失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"构建系统提示失败: {str(e)}")
    
    messages = efficient_data.get("messages", [])
    
    from graph.session_manager import SummaryManager
    summary_manager = SummaryManager.from_data(efficient_data)
    system_msg = summary_manager.to_system_message()
    
    try:
        if system_msg:
            compressed_content = system_msg.get("content", "")
            combined_system = f"{system_prompt}\n\n[历史对话摘要]\n{compressed_content}"
            full_messages = [{"role": "system", "content": combined_system}] + messages
        else:
            full_messages = [
                {"role": "system", "content": system_prompt}
            ] + messages
    except Exception as e:
        logger.error(f"合并系统提示失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"合并系统提示失败: {str(e)}")
    
    logger.debug(f"获取会话消息 [{session_id}]: {len(full_messages)} 条消息")
    
    return {
        "session_id": session_id,
        "messages": full_messages
    }


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """获取对话历史（不含 System Prompt）- 用于前端显示"""
    # 加载原始对话记录（完整消息）
    try:
        original_data = agent_manager.session_manager.load_original_session(session_id)
    except FileNotFoundError:
        logger.warning(f"获取历史失败，会话不存在: {session_id}")
        raise HTTPException(status_code=404, detail="会话不存在")
    except Exception as e:
        logger.error(f"加载原始会话失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"加载会话失败: {str(e)}")
    
    # 加载有效对话记录获取压缩信息
    try:
        efficient_data = agent_manager.session_manager.load_efficient_session(session_id)
    except FileNotFoundError:
        logger.warning(f"获取压缩信息失败，会话不存在: {session_id}")
        raise HTTPException(status_code=404, detail="会话不存在")
    except Exception as e:
        logger.error(f"加载有效会话失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"加载会话压缩信息失败: {str(e)}")
    
    messages = original_data.get("messages", [])
    
    from graph.session_manager import SummaryManager
    summary_manager = SummaryManager.from_data(efficient_data)
    compressed_context = summary_manager.get_context_string()
    
    logger.debug(f"获取会话历史 [{session_id}]: {len(messages)} 条消息, 标题={original_data.get('title', '')}")
    
    return {
        "session_id": session_id,
        "title": original_data.get("title", ""),
        "created_at": original_data.get("created_at", 0),
        "updated_at": original_data.get("updated_at", 0),
        "compressed_context": compressed_context,
        "compressed_rounds": efficient_data.get("compressed_rounds", 0),
        "last_compressed_index": efficient_data.get("last_compressed_index", -1),
        "messages": messages
    }


@router.post("/sessions/{session_id}/generate-title")
async def generate_session_title(session_id: str):
    """AI 生成标题"""
    # 获取第一条用户消息
    try:
        first_user_msg = agent_manager.session_manager.get_first_user_message(session_id)
    except FileNotFoundError:
        logger.warning(f"生成标题失败，会话不存在: {session_id}")
        raise HTTPException(status_code=404, detail="会话不存在")
    except Exception as e:
        logger.error(f"获取第一条用户消息失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户消息失败: {str(e)}")
    
    if not first_user_msg:
        logger.warning(f"生成标题失败，会话中没有用户消息: {session_id}")
        raise HTTPException(status_code=400, detail="No user message found")
    
    # 生成标题（失败时返回默认标题，与 chat.py 一致）
    try:
        title = await title_generator.generate(first_user_msg)
        agent_manager.session_manager.update_title(session_id, title)
        logger.info(f"生成标题成功 [{session_id}]: {title}")
    except Exception as e:
        # 使用默认标题
        title = first_user_msg[:20] if first_user_msg else "新对话"
        try:
            agent_manager.session_manager.update_title(session_id, title)
        except Exception as update_e:
            logger.error(f"更新默认标题失败 [{session_id}]: {update_e}")
        logger.error(f"AI生成标题失败 [{session_id}]: {e}, 使用默认标题: {title}")
    
    return {"session_id": session_id, "title": title}
