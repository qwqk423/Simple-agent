"""代码差异应用工具 - 结构化大修改（重构函数、替换代码块、批量修改）"""
import re
import sys
from pathlib import Path
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from utils.logger import get_logger

logger = get_logger("ApplyDiffTool")


class ApplyDiffInput(BaseModel):
    """代码差异应用工具的输入参数 - 支持多段结构化修改"""
    path: str = Field(description="要修改的文件路径（绝对路径或相对于工作目录）")
    diff: str = Field(description="SEARCH/REPLACE 格式的差异块，支持多段修改，用分隔线 ### DIFF BLOCK SEPARATOR ### 隔开")


def is_safe_path(root_dir: Path, target_path: str) -> tuple[bool, Optional[str]]:
    """安全检查（通用函数）"""
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


def parse_diff_blocks(diff_text: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """
    解析 diff 文本，提取多个 SEARCH/REPLACE 块
    返回: ([(search1, replace1), (search2, replace2), ...], 错误信息)
    """
    # 首先尝试按分隔线分割多个 diff 块
    # 使用独特的分隔符避免与普通代码内容（如 Markdown 水平线、YAML 分隔符）冲突
    separator_pattern = r'\n?### DIFF BLOCK SEPARATOR ###\s*\n?'
    blocks = re.split(separator_pattern, diff_text)

    results = []
    pattern = r'<<<<<<<\s*SEARCH\s*\n?(.*?)\n?=======\s*\n?(.*?)\n?>>>>>>>\s*REPLACE'

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        match = re.search(pattern, block, re.DOTALL)
        if match:
            search_content = match.group(1).rstrip('\n')
            replace_content = match.group(2).rstrip('\n')

            if search_content:
                results.append((search_content, replace_content))

    if not results:
        # 尝试整体匹配（单块模式）
        match = re.search(pattern, diff_text, re.DOTALL)
        if match:
            search_content = match.group(1).rstrip('\n')
            replace_content = match.group(2).rstrip('\n')
            if search_content:
                results.append((search_content, replace_content))
        else:
            logger.warning("无法解析 diff 格式")
            return [], "无法解析 diff 格式，请使用标准的 SEARCH/REPLACE 块格式"

    logger.debug(f"解析到 {len(results)} 个 diff 块")
    return results, None


def find_line_number(content: str, position: int) -> int:
    """根据字符位置计算行号"""
    return content[:position].count('\n') + 1


def apply_diff_logic(root_dir: Path, file_path: str, diff: str) -> str:
    """
    核心逻辑实现：应用结构化差异到文件
    支持多段 SEARCH/REPLACE 批量修改
    """
    # 安全检查
    safe, msg = is_safe_path(root_dir, file_path)
    if not safe:
        return f"[安全拦截] {msg}"

    try:
        target = (root_dir / file_path).resolve()

        # 检查文件是否存在
        if not target.exists():
            logger.warning(f"文件不存在: {file_path}")
            return f"[错误] 文件不存在: {file_path}"

        if target.is_dir():
            logger.warning(f"路径是目录而非文件: {file_path}")
            return f"[错误] 路径是目录，不是文件: {file_path}"

        # 读取原文件内容
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            original_content = f.read()

        # 解析所有 diff 块
        diff_blocks, error = parse_diff_blocks(diff)
        if error:
            return f"[错误] {error}"

        if not diff_blocks:
            logger.warning("没有找到有效的 SEARCH/REPLACE 块")
            return "[错误] 没有找到有效的 SEARCH/REPLACE 块"

        # 验证所有 SEARCH 内容是否都能匹配（预先检查）
        current_content = original_content
        validation_errors = []

        for i, (search_content, _) in enumerate(diff_blocks, 1):
            if search_content not in current_content:
                # 尝试忽略尾部空白匹配
                search_normalized = search_content.rstrip()
                content_normalized = current_content.rstrip()

                if search_normalized not in content_normalized:
                    # 尝试查找最相似的部分
                    hint = ""
                    lines = search_content.strip().split('\n')
                    if lines:
                        first_line = lines[0].strip()
                        if first_line and first_line in current_content:
                            pos = current_content.find(first_line)
                            line_num = find_line_number(current_content, pos)
                            hint = f"（找到相似开头 '{first_line[:30]}...' 在第 {line_num} 行）"

                    validation_errors.append(f"  块 #{i}: 无法找到匹配的 SEARCH 内容 {hint}")
                else:
                    validation_errors.append(f"  块 #{i}: 找到内容但尾部空白不匹配（换行数量不同）")

        if validation_errors:
            logger.warning(f"diff 验证失败: {len(validation_errors)} 个块无法匹配")
            return (
                f"[错误] 发现 {len(validation_errors)} 个无法匹配的 SEARCH 块:\n" +
                '\n'.join(validation_errors) +
                "\n\n提示: SEARCH 内容必须与文件内容完全一致（包括缩进和换行）"
            )

        # 执行所有替换
        current_content = original_content
        replaced_count = 0
        changes = []

        for i, (search_content, replace_content) in enumerate(diff_blocks, 1):
            if search_content in current_content:
                # 记录修改位置
                pos = current_content.find(search_content)
                start_line = find_line_number(current_content, pos)
                end_line = find_line_number(current_content, pos + len(search_content))

                current_content = current_content.replace(search_content, replace_content, 1)
                replaced_count += 1

                # 计算新内容的行数
                new_lines = replace_content.count('\n')
                new_end_line = start_line + new_lines

                line_range = f"{start_line}" if start_line == end_line else f"{start_line}-{end_line}"
                new_range = f"{start_line}" if new_lines == 0 else f"{start_line}-{new_end_line}"

                changes.append(f"  修改 #{i}: 行{line_range} → 行{new_range}")

        # 写入文件
        with open(target, "w", encoding="utf-8") as f:
            f.write(current_content)

        # 生成结果摘要
        result_lines = [
            f"[成功] 已应用 {replaced_count} 处修改到: {file_path}",
            "修改详情:"
        ]
        result_lines.extend(changes)

        # 统计信息
        old_lines = original_content.count('\n') + 1
        new_lines = current_content.count('\n') + 1
        line_diff = new_lines - old_lines

        result_lines.append(f"\n统计: {old_lines}行 → {new_lines}行 ({'+' if line_diff >= 0 else ''}{line_diff})")

        logger.info(f"diff 应用成功: {file_path}, {replaced_count} 处修改")
        return '\n'.join(result_lines)

    except PermissionError as e:
        logger.error(f"应用 diff 权限不足: {file_path}, {e}")
        return f"[错误] 应用差异失败: 权限不足 {e}"
    except Exception as e:
        logger.error(f"应用 diff 失败: {file_path}, {type(e).__name__}: {e}")
        return f"[错误] 应用差异失败: {str(e)}"


def create_apply_diff_tool(base_dir: Path) -> BaseTool:
    """创建代码差异应用工具 - 用于结构化大修改"""
    root_dir = (base_dir / "workspace").resolve()
    logger.debug(f"代码差异应用工具工作目录: {root_dir}")

    def apply_diff_func(path: str, diff: str) -> str:
        """工具入口函数"""
        if not path:
            logger.warning("path 为空")
            return "[错误] path 不能为空"

        if not diff:
            logger.warning("diff 为空")
            return "[错误] diff 不能为空"

        logger.debug(f"应用 diff: {path}, diff长度={len(diff)}")
        return apply_diff_logic(root_dir, path, diff)

    return StructuredTool.from_function(
        name="apply_diff",
        description=f"""结构化大修改文件内容 - 重构函数、批量多段替换。

【适用场景 - 复杂修改】
- 重构整个函数或类
- 替换大段代码块（>10行）
- 一次修改多处代码（批量替换）
- 需要精确控制替换边界

【不适用场景 - 用 edit_file】
- 简单变量名修改
- 单行bug修复
- 少量文本替换

【工作目录】 {base_dir / "workspace"}

【参数】
- path: 文件路径
- diff: SEARCH/REPLACE 格式的差异块，多段用 ### DIFF BLOCK SEPARATOR ### 分隔

【格式规范】
<<<<<<< SEARCH
[要替换的原始代码 - 必须完全匹配]
=======
[新代码]
>>>>>>> REPLACE
### DIFF BLOCK SEPARATOR ###
<<<<<<< SEARCH
[第二段要替换的代码]
=======
[第二段新代码]
>>>>>>> REPLACE

【关键规则 - 严格遵守】
1. SEARCH 必须与文件内容完全一致（包括缩进、空格和换行）
2. 多段修改用 ### DIFF BLOCK SEPARATOR ### 分隔
3. 所有 SEARCH 先验证，全部通过后才执行
4. 每段只替换第一处匹配
5. 如果匹配失败，会提示相似内容的位置

【使用流程】
1. read_file 查看文件内容
2. 规划修改，拆分多个 SEARCH/REPLACE 块
3. 每块包含足够的上下文确保唯一匹配
4. 调用 apply_diff 批量应用

【示例】批量修改导入和函数
<<<<<<< SEARCH
import json
=======
import json
from typing import Dict, Any
>>>>>>> REPLACE
### DIFF BLOCK SEPARATOR ###
<<<<<<< SEARCH
def process(data):
    return json.loads(data)
=======
def process(data: str) -> Dict[str, Any]:
    return json.loads(data)
>>>>>>> REPLACE

【工具选择】
┌─────────────┬─────────────────────────┬─────────────────────────┐
│   场景      │      推荐工具           │         原因            │
├─────────────┼─────────────────────────┼─────────────────────────┤
│ 小修改(<10) │ edit_file              │ 简单直接，操作快捷      │
│ 大修改/重构 │ apply_diff             │ 支持多段，批量替换      │
│ 创建新文件  │ write_file             │ 直接写入完整内容        │
└─────────────┴─────────────────────────┴─────────────────────────┘
""",
        func=apply_diff_func,
        args_schema=ApplyDiffInput
    )
