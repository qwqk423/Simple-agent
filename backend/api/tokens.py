"""Token 统计 API"""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from graph.agent import agent_manager
from graph.prompt_builder import PromptBuilder, count_tokens
from utils.logger import get_logger

logger = get_logger("TokensAPI")

router = APIRouter()


class TokenFilesRequest(BaseModel):
    """批量统计文件请求"""
    paths: List[str]


@router.get("/tokens/session/{session_id}")
async def get_session_tokens(session_id: str):
    """获取会话 Token 统计"""
    logger.debug(f"获取会话Token统计 [{session_id}]")
    
    # 获取 System Prompt tokens
    try:
        prompt_builder = PromptBuilder(agent_manager.base_dir)
        system_info = prompt_builder.get_all_files_tokens()
    except Exception as e:
        logger.error(f"获取系统提示Token失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统提示Token失败: {str(e)}")
    
    # 获取消息 tokens（使用原始对话记录）
    try:
        session_data = agent_manager.session_manager.load_original_session(session_id)
    except FileNotFoundError:
        logger.warning(f"获取Token统计失败，会话不存在: {session_id}")
        raise HTTPException(status_code=404, detail="会话不存在")
    except Exception as e:
        logger.error(f"加载会话数据失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"加载会话数据失败: {str(e)}")
    
    messages = session_data.get("messages", [])
    
    message_tokens = 0
    tool_call_count = 0
    tool_result_count = 0
    
    for msg in messages:
        try:
            # 计算消息内容 token
            content = msg.get("content", "")
            content_tokens = count_tokens(content)
            message_tokens += content_tokens
            
            # 计算工具调用 token
            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                tool_call_count += 1
                # 工具名称
                tool_name = tc.get("function", {}).get("name", "")
                message_tokens += count_tokens(tool_name)
                # 工具参数
                tool_args = tc.get("function", {}).get("arguments", "")
                message_tokens += count_tokens(str(tool_args))
            
            # 计算工具返回 token（role == "tool" 的消息）
            if msg.get("role") == "tool":
                tool_result_count += 1
                tool_content = msg.get("content", "")
                message_tokens += count_tokens(tool_content)
        except Exception as e:
            logger.warning(f"计算单条消息Token失败 [{session_id}]: {e}, msg_role={msg.get('role')}")
            # 继续处理其他消息
    
    total_tokens = system_info["total_tokens"] + message_tokens
    
    logger.debug(f"Token统计结果 [{session_id}]: 系统={system_info['total_tokens']}, "
                f"消息={message_tokens}, 总计={total_tokens}, "
                f"工具调用={tool_call_count}, 工具结果={tool_result_count}")
    
    return {
        "session_id": session_id,
        "system_tokens": system_info["total_tokens"],
        "message_tokens": message_tokens,
        "total_tokens": total_tokens,
        "system_files": system_info["files"],
        "message_count": len(messages),
        "tool_call_count": tool_call_count,
        "tool_result_count": tool_result_count
    }


@router.post("/tokens/files")
async def get_files_tokens(request: TokenFilesRequest):
    """批量统计文件 Token"""
    logger.debug(f"批量统计文件Token: {len(request.paths)} 个文件")
    
    base_dir = agent_manager.base_dir
    results = []
    
    for path in request.paths:
        file_path = base_dir / path
        
        if not file_path.exists():
            logger.debug(f"文件不存在: {path}")
            results.append({
                "path": path,
                "exists": False,
                "chars": 0,
                "tokens": 0
            })
            continue
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tokens = count_tokens(content)
            results.append({
                "path": path,
                "exists": True,
                "readable": True,
                "chars": len(content),
                "tokens": tokens
            })
            logger.debug(f"文件Token统计 [{path}]: {len(content)}字符, {tokens}tokens")
        except UnicodeDecodeError as e:
            logger.warning(f"文件编码错误 [{path}]: {e}")
            results.append({
                "path": path,
                "exists": True,
                "readable": False,
                "error": f"文件编码错误: {str(e)}",
                "chars": 0,
                "tokens": 0
            })
        except PermissionError as e:
            logger.warning(f"读取文件权限不足 [{path}]: {e}")
            results.append({
                "path": path,
                "exists": True,
                "readable": False,
                "error": f"权限不足: {str(e)}",
                "chars": 0,
                "tokens": 0
            })
        except Exception as e:
            logger.error(f"读取文件失败 [{path}]: {e}")
            results.append({
                "path": path,
                "exists": True,
                "readable": False,
                "error": str(e),
                "chars": 0,
                "tokens": 0
            })
    
    total_tokens = sum(r["tokens"] for r in results if r.get("exists"))
    total_chars = sum(r["chars"] for r in results if r.get("exists"))
    
    logger.info(f"批量Token统计完成: {len(request.paths)} 个文件, "
                f"总计 {total_chars} 字符, {total_tokens} tokens")
    
    return {
        "files": results,
        "total_tokens": total_tokens,
        "total_chars": total_chars,
        "file_count": len(request.paths),
        "success_count": sum(1 for r in results if r.get("readable"))
    }
