"""对话压缩 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from graph.agent import agent_manager
from utils.llm_factory import create_llm
from utils.logger import get_logger

logger = get_logger("CompressAPI")

router = APIRouter()


class CompressPreviewResponse(BaseModel):
    """压缩预览响应"""
    session_id: str
    new_messages_count: int
    total_messages_count: int
    request_detail: str  # JSON 格式的云端请求详情
    can_compress: bool


class CompressExecuteRequest(BaseModel):
    """执行压缩请求"""
    confirm: bool = True


class CompressExecuteResponse(BaseModel):
    """执行压缩响应"""
    session_id: str
    compressed_count: int
    compressed_rounds: int
    merged: bool
    merged_rounds: int | None
    summary: str


@router.get("/sessions/{session_id}/compress/preview")
async def get_compress_preview(session_id: str):
    """获取压缩预览（用于二次确认弹窗显示请求详情）"""
    logger.info(f"获取压缩预览 [{session_id}]")
    
    try:
        new_messages, efficient_data, request_detail = agent_manager.session_manager.prepare_compression(session_id)
        
        # 加载原始会话获取总消息数
        try:
            original_data = agent_manager.session_manager.load_original_session(session_id)
        except FileNotFoundError:
            logger.warning(f"会话不存在 [{session_id}]")
            raise HTTPException(status_code=404, detail="会话不存在")
        except Exception as e:
            logger.error(f"加载原始会话失败 [{session_id}]: {e}")
            raise HTTPException(status_code=500, detail=f"加载会话失败: {str(e)}")
        
        total_messages = len(original_data.get("messages", []))
        can_compress = len(new_messages) > 0
        
        logger.info(f"压缩预览结果 [{session_id}]: 新消息={len(new_messages)}, 总消息={total_messages}, 可压缩={can_compress}")
        
        return {
            "session_id": session_id,
            "new_messages_count": len(new_messages),
            "total_messages_count": total_messages,
            "request_detail": request_detail,
            "can_compress": can_compress
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取压缩预览失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"获取压缩预览失败: {str(e)}")


@router.post("/sessions/{session_id}/compress")
async def compress_session(session_id: str, request: CompressExecuteRequest | None = None):
    """执行对话压缩
    
    流程：
    1. 准备压缩数据（获取新增消息）
    2. 调用 LLM 生成摘要
    3. 执行压缩（更新 efficient 文件）
    4. 返回结果
    """
    logger.info(f"开始执行对话压缩 [{session_id}]")
    
    try:
        # 准备压缩数据
        try:
            new_messages, efficient_data, request_detail = agent_manager.session_manager.prepare_compression(session_id)
        except FileNotFoundError:
            logger.warning(f"会话不存在 [{session_id}]")
            raise HTTPException(status_code=404, detail="会话不存在")
        except ValueError as e:
            logger.warning(f"压缩数据准备失败 [{session_id}]: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"准备压缩数据失败 [{session_id}]: {e}")
            raise HTTPException(status_code=500, detail=f"准备压缩数据失败: {str(e)}")
        
        if not new_messages:
            logger.warning(f"没有新消息需要压缩 [{session_id}]")
            raise HTTPException(status_code=400, detail="没有新消息需要压缩")
        
        logger.debug(f"准备压缩 {len(new_messages)} 条新消息 [{session_id}]")
        
        # 解析请求详情获取实际要发送的内容
        import json
        try:
            detail_obj = json.loads(request_detail)
            prompt_content = detail_obj["messages"][1]["content"]
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"解析请求详情失败 [{session_id}]: {e}")
            raise HTTPException(status_code=500, detail=f"解析请求详情失败: {str(e)}")
        
        # 调用 LLM 生成摘要
        try:
            llm = create_llm(temperature=0.3, override_params={"thinking_enabled": False})
            logger.debug(f"调用LLM生成摘要 [{session_id}]")
            
            response = await llm.ainvoke(prompt_content)
            summary = response.content.strip()
            
            logger.debug(f"摘要生成完成 [{session_id}]: 长度={len(summary)}")
        except Exception as e:
            logger.error(f"LLM生成摘要失败 [{session_id}]: {e}")
            raise HTTPException(status_code=500, detail=f"生成摘要失败: {str(e)}")
        
        # 执行压缩
        try:
            result = agent_manager.session_manager.execute_compression(
                session_id, summary, new_messages, efficient_data
            )
            logger.info(f"对话压缩完成 [{session_id}]: 压缩{result['compressed_count']}条消息, "
                       f"{result['compressed_rounds']}轮对话, 合并={result['merged']}")
        except FileNotFoundError:
            logger.warning(f"会话不存在 [{session_id}]")
            raise HTTPException(status_code=404, detail="会话不存在")
        except Exception as e:
            logger.error(f"执行压缩失败 [{session_id}]: {e}")
            raise HTTPException(status_code=500, detail=f"执行压缩失败: {str(e)}")
        
        return {
            "session_id": session_id,
            "compressed_count": result["compressed_count"],
            "compressed_rounds": result["compressed_rounds"],
            "merged": result["merged"],
            "merged_rounds": result["merged_rounds"],
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"压缩失败 [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"压缩失败: {str(e)}")
