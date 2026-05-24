"""文件编辑工具 - 快速小修改（修改变量、修复bug、单行/少量行编辑）"""
import re
import sys
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from utils.logger import get_logger

logger = get_logger("EditFileTool")


class EditFileInput(BaseModel):
    """文件编辑工具的输入参数 - 专为快速小修改设计"""
    path: str = Field(description="要修改的文件路径（绝对路径或相对于工作目录）")
    old_str: str = Field(description="要替换的原始文本（必须完全匹配，建议包含足够的上下文确保唯一性）")
    new_str: str = Field(description="替换后的新文本")


def is_safe_path(root_dir: Path, target_path: str) -> tuple[bool, Optional[str]]:
    """安全检查：确保路径在工作目录内"""
    try:
        if Path(target_path).is_absolute():
            target = Path(target_path).resolve()
        else:
            target = (root_dir / target_path).resolve()

        target.relative_to(root_dir)
    except ValueError:
        logger.warning(f"路径逃逸检测: {target_path}")
        return False, "路径逃逸检测: 禁止访问工作目录外的文件"

    if ".." in target_path or "~" in target_path:
        logger.warning(f"路径包含非法字符: {target_path}")
        return False, "路径包含非法字符"

    return True, None


def find_line_number(content: str, position: int) -> int:
    """根据字符位置计算行号"""
    return content[:position].count('\n') + 1


def edit_file_logic(
    root_dir: Path,
    path: str,
    old_str: str,
    new_str: str
) -> str:
    """
    核心逻辑：快速编辑文件，将 old_str 替换为 new_str
    专为小范围修改设计：修变量名、改函数参数、调整单行逻辑等
    """
    # 安全检查
    safe, msg = is_safe_path(root_dir, path)
    if not safe:
        return f"[安全拦截] {msg}"

    try:
        # 解析目标路径
        if Path(path).is_absolute():
            target = Path(path).resolve()
        else:
            target = (root_dir / path).resolve()

        # 检查文件
        if not target.exists():
            logger.warning(f"文件不存在: {path}")
            return f"[错误] 文件不存在: {path}"

        if target.is_dir():
            logger.warning(f"路径是目录而非文件: {path}")
            return f"[错误] 路径是目录，不是文件: {path}"

        # 读取原文件内容
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            original_content = f.read()

        # 检查 old_str 是否存在
        if old_str not in original_content:
            # 尝试去除首尾空白后匹配，给出更友好的错误提示
            old_stripped = old_str.strip()
            content_stripped = original_content.strip()

            if old_stripped in content_stripped:
                # 查找相似内容的位置
                idx = content_stripped.find(old_stripped)
                line_num = find_line_number(original_content, idx)
                logger.warning(f"找到相似内容但空白字符不匹配: {path}, 第 {line_num} 行")
                return (
                    f"[错误] 找到相似内容但空白字符（缩进/换行）不匹配。\n"
                    f"      相似内容位于第 {line_num} 行附近。\n"
                    f"      建议：复制文件中 exact 的内容，包括缩进"
                )

            # 尝试查找关键字给出提示
            if len(old_str) > 10:
                key_parts = [p for p in old_str.split('\n')[0].split() if len(p) > 3][:3]
                if key_parts:
                    hints = []
                    for part in key_parts:
                        if part in original_content:
                            count = original_content.count(part)
                            positions = []
                            start = 0
                            for _ in range(min(count, 3)):
                                pos = original_content.find(part, start)
                                line = find_line_number(original_content, pos)
                                positions.append(f"第{line}行")
                                start = pos + 1
                            hint = f"  - '{part}' 出现在 {', '.join(positions)}"
                            if count > 3:
                                hint += f" 等共{count}处"
                            hints.append(hint)

                    if hints:
                        logger.warning(f"未找到完全匹配的 old_str，但找到关键字: {path}")
                        return (
                            f"[错误] 无法在文件中找到完全匹配的 old_str\n"
                            f"      但找到以下关键字，供您参考:\n" +
                            '\n'.join(hints) +
                            "\n      建议：复制 exact 的代码片段（包括缩进）"
                        )

            logger.warning(f"未找到匹配的 old_str: {path}")
            return f"[错误] 无法在文件中找到匹配的 old_str 内容"

        # 检查匹配次数
        match_count = original_content.count(old_str)

        if match_count > 1:
            # 找到所有匹配位置
            positions = []
            start = 0
            for i in range(min(match_count, 5)):
                pos = original_content.find(old_str, start)
                line_num = find_line_number(original_content, pos)
                positions.append(f"第{line_num}行")
                start = pos + 1

            extra = f" 等共{match_count}处" if match_count > 5 else ""
            logger.warning(f"找到多处匹配: {path}, 位置: {', '.join(positions)}{extra}")

            return (
                f"[错误] 找到 {match_count} 处匹配，无法确定替换哪一处\n"
                f"      匹配位置: {', '.join(positions)}{extra}\n"
                f"      建议: 提供更精确的 old_str（包含更多上下文代码）确保唯一匹配"
            )

        # 执行替换（仅替换第一处且唯一的一处）
        new_content = original_content.replace(old_str, new_str, 1)

        # 如果内容没有变化
        if new_content == original_content:
            logger.warning(f"替换后内容未发生变化: {path}")
            return "[警告] 替换后内容未发生变化"

        # 写入文件
        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)

        # 计算修改范围
        pos = original_content.find(old_str)
        old_lines = original_content[:pos].count('\n') + 1
        old_end_lines = original_content[:pos + len(old_str)].count('\n') + 1
        new_line_count = new_str.count('\n')
        new_end_lines = old_lines + new_line_count

        # 显示简洁的修改摘要
        line_info = f"第{old_lines}行" if old_lines == old_end_lines else f"第{old_lines}-{old_end_lines}行"
        new_line_info = f"第{old_lines}行" if new_line_count == 0 else f"第{old_lines}-{new_end_lines}行"

        logger.info(f"文件编辑成功: {path}, {line_info}, 变更: {len(old_str)} -> {len(new_str)} 字符")

        return (
            f"[成功] 已修改 {path}\n"
            f"      原位置: {line_info}\n"
            f"      新位置: {new_line_info}\n"
            f"      变更: {len(old_str)} 字符 → {len(new_str)} 字符"
        )

    except PermissionError as e:
        logger.error(f"编辑文件权限不足: {path}, {e}")
        return f"[错误] 编辑文件失败: 权限不足 {e}"
    except Exception as e:
        logger.error(f"编辑文件失败: {path}, {type(e).__name__}: {e}")
        return f"[错误] 编辑文件失败: {str(e)}"


def create_edit_file_tool(base_dir: Path) -> BaseTool:
    """创建文件编辑工具 - 用于快速小修改"""
    root_dir = (base_dir / "workspace").resolve()
    logger.debug(f"文件编辑工具工作目录: {root_dir}")

    def edit_file_func(
        path: str,
        old_str: str,
        new_str: str
    ) -> str:
        """工具入口函数"""
        if not path:
            logger.warning("path 为空")
            return "[错误] path 不能为空"

        if not old_str:
            logger.warning("old_str 为空")
            return "[错误] old_str 不能为空"

        logger.debug(f"编辑文件: {path}")
        return edit_file_logic(root_dir, path, old_str, new_str)

    return StructuredTool.from_function(
        name="edit_file",
        description=f"""快速小修改文件内容（<10行）- 修改变量、修复bug。

【适用场景 - 简单修改】
- 修改变量名、函数名
- 修改单个参数值
- 修复语法错误（如 `=` 改成 `==`）
- 添加/删除单行代码
- 简单文本替换（10行以内）

【不适用场景 - 用 apply_diff】
- 重构整个函数或类
- 批量多处修改
- 大范围结构调整

【工作目录】 {base_dir / "workspace"}

【参数】
- path: 文件路径
- old_str: 要替换的原始文本（必须完全匹配，建议包含足够上下文确保唯一性）
- new_str: 替换后的新文本

【关键规则】
1. old_str 必须完全匹配（包括缩进和换行）
2. 确保 old_str 在文件中唯一，否则报错
3. 只替换第一处匹配

【使用流程】
1. 先用 read_file 查看文件内容
2. 复制要修改的 exact 代码片段作为 old_str
3. 编写 new_str 进行替换

【示例】修改变量名
  old_str: 'user_name = input("Enter name: ")'
  new_str: 'username = input("Enter name: ")'

【示例】修复语法错误
  old_str: "if x = 10:"
  new_str: "if x == 10:"

【工具选择】
┌─────────────┬─────────────────────────┬─────────────────────────┐
│   场景      │      推荐工具           │         原因            │
├─────────────┼─────────────────────────┼─────────────────────────┤
│ 小修改(<10) │ edit_file              │ 简单直接，操作快捷      │
│ 大修改/重构 │ apply_diff             │ 支持多段替换，结构化    │
│ 创建新文件  │ write_file             │ 直接写入完整内容        │
└─────────────┴─────────────────────────┴─────────────────────────┘
""",
        func=edit_file_func,
        args_schema=EditFileInput
    )
