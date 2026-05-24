"""文件读取工具 - 直接读取已知路径的文件内容"""
import re
import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from utils.logger import get_logger

logger = get_logger("ReadFileTool")


def is_safe_path(root_dir: Path, file_path: str) -> tuple[bool, Optional[str]]:
    """检查路径是否安全"""
    # 解析路径
    try:
        target = (root_dir / file_path).resolve()
    except Exception as e:
        logger.warning(f"无效的路径: {file_path}, {e}")
        return False, f"无效的路径: {str(e)}"

    # 检查是否在 root_dir 内
    try:
        target.relative_to(root_dir)
    except ValueError:
        logger.warning(f"路径逃逸检测: {file_path}")
        return False, f"路径逃逸检测: 禁止访问项目目录外的文件"

    # 检查路径遍历攻击
    if ".." in file_path:
        logger.warning(f"路径包含非法字符 '..': {file_path}")
        return False, "路径包含非法字符 .."

    if "~" in file_path:
        logger.warning(f"路径包含非法字符 '~': {file_path}")
        return False, "路径包含非法字符 ~"

    return True, None


def read_file_content(root_dir: Path, file_path: str, max_chars: int = 10000) -> str:
    """读取文件内容"""
    safe, msg = is_safe_path(root_dir, file_path)
    if not safe:
        return f"[安全拦截] {msg}"

    try:
        target = (root_dir / file_path).resolve()

        if not target.exists():
            logger.warning(f"文件不存在: {file_path}")
            return f"[错误] 文件不存在: {file_path}"

        if target.is_dir():
            logger.warning(f"路径是目录而非文件: {file_path}")
            return f"[错误] 路径是目录，不是文件: {file_path}"

        # 读取文件
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 记录原始大小
        total_chars = len(content)

        # 截断输出
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n...[内容已截断，共 {total_chars} 字符]"
            logger.debug(f"文件内容截断: {file_path} ({total_chars} -> {max_chars} 字符)")

        logger.info(f"文件读取成功: {file_path}, 大小={total_chars} 字符")
        return content

    except PermissionError as e:
        logger.error(f"读取文件权限不足: {file_path}, {e}")
        return f"[错误] 读取失败: 权限不足 {e}"
    except UnicodeDecodeError as e:
        logger.error(f"文件编码错误: {file_path}, {e}")
        return f"[错误] 读取失败: 编码错误 {e}"
    except Exception as e:
        logger.error(f"读取文件失败: {file_path}, {type(e).__name__}: {e}")
        return f"[错误] 读取失败: {str(e)}"


class ReadFileInput(BaseModel):
    """文件读取工具的输入参数"""
    file_path: str = Field(description="文件路径（相对路径），如 'config.py', 'src/utils/helper.py'")

def create_read_file_tool(base_dir: Path) -> BaseTool:
    """创建文件读取工具"""
    root_dir = (base_dir / "workspace").resolve()
    logger.debug(f"文件读取工具工作目录: {root_dir}")

    def read_func(file_path: str) -> str:
        """读取指定文件的内容"""
        if not file_path or not file_path.strip():
            logger.warning("文件路径为空")
            return "[错误] 文件路径不能为空"

        logger.debug(f"读取文件: {file_path}")
        return read_file_content(root_dir, file_path)

    return StructuredTool.from_function(
        name="read_file",
        description=f"""读取指定文件的内容 - 必须知道确切文件路径。

【适用场景】
- 已通过 grep/search_codebase 找到文件路径
- 查看配置文件、代码文件内容
- 读取后要使用 edit_file/apply_diff 修改

【不适用场景】
- 不知道文件路径（先用 grep 或 search_codebase 查找）
- 批量搜索代码模式（用 grep）
- 模糊概念搜索（用 search_codebase）

【工作目录】 {base_dir / "workspace"}

【参数】
- file_path (字符串, 必需): 文件路径（相对路径）
  示例: "config.py"
  示例: "src/utils/helper.py"
  示例: "README.md"

【使用流程】
1. 先用 search_codebase/grep/glob 找到文件
2. 再用 read_file 读取内容
3. 如需修改，使用 edit_file 或 apply_diff

【示例】
file_path="src/main.py"

【文件操作工具选择】
┌─────────────┬─────────────────────────┬─────────────────────────┐
│   场景      │      推荐工具           │         原因            │
├─────────────┼─────────────────────────┼─────────────────────────┤
│ 读取文件    │ read_file              │ 已知路径，直接读取      │
│ 小修改      │ edit_file              │ 简单替换，<10行         │
│ 大修改      │ apply_diff             │ 多段批量替换            │
│ 创建/覆盖   │ write_file             │ 写入完整内容            │
└─────────────┴─────────────────────────┴─────────────────────────┘

【搜索工具选择】
┌─────────────────────┬─────────────────────┬─────────────────────────┐
│ 找文件路径          │     推荐工具        │         原因            │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ 模糊概念/语义       │ search_codebase    │ 理解意图搜索            │
│ 知道函数/变量名     │ grep               │ 精确匹配                │
│ 找某类型文件        │ glob               │ 按文件名模式            │
│ 浏览目录            │ list_workspace     │ 目录树展示              │
└─────────────────────┴─────────────────────┴─────────────────────────┘
""",
        func=read_func,
        args_schema=ReadFileInput
    )
