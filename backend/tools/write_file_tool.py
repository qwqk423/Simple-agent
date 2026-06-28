"""文件写入工具"""
import sys
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from utils.logger import get_logger

logger = get_logger("WriteFileTool")


class WriteFileInput(BaseModel):
    """文件写入工具的输入参数"""
    file_path: str = Field(description="要写入的文件路径（相对于工作目录，如 'src/main.py'）")
    content: str = Field(description="要写入文件的内容")
    rewrite: bool = Field(default=False, description="是否覆盖现有文件，默认为 false")


def is_safe_path(root_dir: Path, target_path: str) -> tuple[bool, Optional[str]]:
    """安全检查（通用函数，可复用）"""
    try:
        target = (root_dir / target_path).resolve()
        target.relative_to(root_dir)
    except ValueError:
        logger.warning(f"路径逃逸检测: {target_path}")
        return False, "路径逃逸检测: 禁止访问项目目录外的文件"

    if ".." in target_path or "~" in target_path:
        logger.warning(f"路径包含非法字符: {target_path}")
        return False, "路径包含非法字符"

    return True, None


def write_file_logic(root_dir: Path, file_path: str, content: str, rewrite: bool = False) -> str:
    """核心逻辑实现：将内容写入本地文件系统"""
    # 安全检查
    safe, msg = is_safe_path(root_dir, file_path)
    if not safe:
        return f"[安全拦截] {msg}"

    try:
        target = (root_dir / file_path).resolve()

        # 在写入前记录文件是否存在，用于后续 action 判断
        file_existed = target.exists()

        # 检查文件是否已存在
        if file_existed and not rewrite:
            logger.warning(f"文件已存在且未设置 rewrite: {file_path}")
            return f"[错误] 文件已存在: {file_path}，如需覆盖请设置 rewrite=true"

        # 自动创建父目录
        target.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"创建父目录: {target.parent}")

        # 写入文件
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        action = "覆盖" if file_existed and rewrite else "创建"
        logger.info(f"文件已{action}: {file_path}, 大小={len(content)} 字符")
        return f"[成功] 文件已{action}: {file_path}"

    except PermissionError as e:
        logger.error(f"写入文件权限不足: {file_path}, {e}")
        return f"[错误] 写入失败: 权限不足 {e}"
    except OSError as e:
        logger.error(f"写入文件系统错误: {file_path}, {type(e).__name__}: {e}")
        return f"[错误] 写入失败: 系统错误 {e}"
    except Exception as e:
        logger.error(f"写入文件失败: {file_path}, {type(e).__name__}: {e}")
        return f"[错误] 写入失败: {str(e)}"


def create_write_file_tool(base_dir: Path) -> BaseTool:
    """创建文件写入工具（工厂函数）"""
    root_dir = (base_dir / "workspace").resolve()
    logger.debug(f"文件写入工具工作目录: {root_dir}")

    def write_func(file_path: str, content: str, rewrite: bool = False) -> str:
        """工具入口函数"""
        # 参数校验
        if not file_path:
            logger.warning("file_path 为空")
            return "[错误] file_path 不能为空"

        if content is None:
            logger.warning("content 为 None")
            return "[错误] content 不能为空"

        logger.debug(f"写入文件: {file_path}, rewrite={rewrite}, content长度={len(content)}")
        return write_file_logic(root_dir, file_path, content, rewrite)

    return StructuredTool.from_function(
        name="write_file",
        description=f"""创建新文件或完全覆盖现有文件。

【适用场景】
- 创建全新的代码文件
- 完全重写一个已有文件（会丢失原内容，谨慎使用）
- 首次写入配置文件

【不适用场景】
- 小修改（用 edit_file）
- 大修改/重构（用 apply_diff）
- 追加内容（先 read_file 再 edit_file）

【工作目录】 {base_dir / "workspace"}

【参数】
- file_path: 文件路径（相对路径，如 "src/main.py"）
- content: 要写入的完整内容
- rewrite: 是否覆盖已有文件，默认 false

【重要规则】
1. 覆盖现有文件前必须先 read_file 查看原内容
2. 优先使用 edit_file 或 apply_diff 进行编辑，而非覆盖
3. 此工具会完全替换文件内容，无法恢复

【工具对比】
- write_file: 创建/完全覆盖文件（破坏性强）
- edit_file: 小范围替换（推荐用于修改）
- apply_diff: 结构化多段修改（推荐用于重构）
""",
        func=write_func,
        args_schema=WriteFileInput
    )
