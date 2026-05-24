"""文件操作 API"""
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from graph.agent import agent_manager
from graph.memory_indexer import get_memory_indexer
from utils.logger import get_logger

logger = get_logger("FilesAPI")

router = APIRouter()


class SaveFileRequest(BaseModel):
    """保存文件请求"""
    path: str
    content: str


# 允许的文件路径前缀
ALLOWED_PREFIXES = ["workspace/", "knowledge/"]
ALLOWED_ROOT_FILES = ["SKILLS_SNAPSHOT.md"]


def is_path_allowed(file_path: str) -> tuple[bool, str]:
    """检查路径是否允许访问"""
    # 检查路径遍历
    if ".." in file_path:
        logger.warning(f"路径包含非法字符 '..': {file_path}")
        return False, "路径包含非法字符 .."
    
    if "~" in file_path:
        logger.warning(f"路径包含非法字符 '~': {file_path}")
        return False, "路径包含非法字符 ~"
    
    if file_path.startswith("/"):
        logger.warning(f"路径以 '/' 开头: {file_path}")
        return False, "路径不能以 / 开头"
    
    # 检查是否在允许的目录下
    for prefix in ALLOWED_PREFIXES:
        if file_path.startswith(prefix):
            return True, ""
    
    # 检查是否是允许的根目录文件
    if file_path in ALLOWED_ROOT_FILES:
        return True, ""
    
    logger.warning(f"路径不在允许范围内: {file_path}")
    return False, f"路径不在允许的范围内，允许的前缀: {ALLOWED_PREFIXES}"


@router.get("/files")
async def read_file(path: str = Query(..., description="文件路径")):
    """读取文件内容"""
    logger.debug(f"读取文件请求: {path}")
    
    allowed, msg = is_path_allowed(path)
    if not allowed:
        raise HTTPException(status_code=403, detail=msg)
    
    base_dir = agent_manager.base_dir
    file_path = base_dir / path
    
    # 确保文件在 base_dir 内
    try:
        file_path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        logger.warning(f"路径逃逸检测: {path}")
        raise HTTPException(status_code=403, detail="路径逃逸检测")
    
    if not file_path.exists():
        logger.debug(f"文件不存在: {path}")
        raise HTTPException(status_code=404, detail="File not found")
    
    if file_path.is_dir():
        logger.warning(f"路径是目录而非文件: {path}")
        raise HTTPException(status_code=400, detail="Path is a directory")
    
    try:
        content = file_path.read_text(encoding="utf-8")
        logger.debug(f"文件读取成功: {path}, 大小={len(content)}字符")
        return {"path": path, "content": content}
    except UnicodeDecodeError as e:
        logger.error(f"文件编码错误 [{path}]: {e}")
        raise HTTPException(status_code=500, detail=f"文件编码错误，无法读取为文本: {str(e)}")
    except PermissionError as e:
        logger.error(f"文件读取权限不足 [{path}]: {e}")
        raise HTTPException(status_code=403, detail=f"读取文件权限不足: {str(e)}")
    except Exception as e:
        logger.error(f"读取文件失败 [{path}]: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.post("/files")
async def save_file(request: SaveFileRequest):
    """保存文件"""
    logger.debug(f"保存文件请求: {request.path}, 内容长度={len(request.content)}")
    
    allowed, msg = is_path_allowed(request.path)
    if not allowed:
        raise HTTPException(status_code=403, detail=msg)
    
    base_dir = agent_manager.base_dir
    file_path = base_dir / request.path
    
    # 确保文件在 base_dir 内
    try:
        file_path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        logger.warning(f"路径逃逸检测: {request.path}")
        raise HTTPException(status_code=403, detail="路径逃逸检测")
    
    # 确保目录存在
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        logger.error(f"创建目录权限不足 [{file_path.parent}]: {e}")
        raise HTTPException(status_code=403, detail=f"创建目录权限不足: {str(e)}")
    except Exception as e:
        logger.error(f"创建目录失败 [{file_path.parent}]: {e}")
        raise HTTPException(status_code=500, detail=f"创建目录失败: {str(e)}")
    
    try:
        file_path.write_text(request.content, encoding="utf-8")
        logger.info(f"文件保存成功: {request.path}, 大小={len(request.content)}字符")
        
        # 如果是 memory 目录下的 YYYY-MM-DD.md 文件，触发索引重建
        if request.path.startswith("workspace/memory/") and request.path.endswith(".md"):
            import re
            if re.match(r'^workspace/memory/\d{4}-\d{2}-\d{2}\.md$', request.path):
                try:
                    indexer = get_memory_indexer(base_dir)
                    indexer.rebuild_index()
                    logger.info(f"{request.path} 已更新，记忆索引重建完成")
                except Exception as e:
                    logger.error(f"重建记忆索引失败: {e}")
        
        return {"path": request.path, "success": True}
    except PermissionError as e:
        logger.error(f"写入文件权限不足 [{request.path}]: {e}")
        raise HTTPException(status_code=403, detail=f"写入文件权限不足: {str(e)}")
    except Exception as e:
        logger.error(f"保存文件失败 [{request.path}]: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@router.get("/skills")
async def list_skills():
    """列出所有可用技能"""
    logger.debug("列出所有技能")
    
    # 延迟导入避免循环导入（skills_scanner 依赖 agent_manager）
    try:
        from tools.skills_scanner import scan_skills
    except ImportError as e:
        logger.error(f"导入 skills_scanner 失败: {e}")
        raise HTTPException(status_code=500, detail="技能扫描模块加载失败")
    
    base_dir = agent_manager.base_dir
    skills_dir = base_dir / "workspace" / "skills"
    
    try:
        skills = scan_skills(skills_dir)
        logger.info(f"扫描到 {len(skills)} 个技能")
        return {"skills": skills}
    except FileNotFoundError:
        logger.warning(f"技能目录不存在: {skills_dir}")
        return {"skills": []}
    except Exception as e:
        logger.error(f"扫描技能失败: {e}")
        raise HTTPException(status_code=500, detail=f"扫描技能失败: {str(e)}")
