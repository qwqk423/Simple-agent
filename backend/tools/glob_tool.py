"""Glob 文件模式匹配工具 - 快速查找匹配特定模式的文件"""
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool


class GlobInput(BaseModel):
    """Glob 工具的输入参数"""
    pattern: str = Field(description="要匹配文件的 glob 模式（如 '**/*.js', 'src/**/*.ts'）")
    path: Optional[str] = Field(default=None, description="要搜索的目录（相对于工作目录，默认当前工作目录）")


def is_safe_path(root_dir: Path, target_path: Optional[str]) -> tuple[bool, Optional[str]]:
    """安全检查"""
    if not target_path:
        return True, None
    
    try:
        target = (root_dir / target_path).resolve()
        target.relative_to(root_dir)
    except ValueError:
        return False, "路径逃逸检测: 禁止访问项目目录外的文件"
    
    if ".." in target_path or "~" in target_path:
        return False, "路径包含非法字符"
    
    return True, None


def glob_files(root_dir: Path, pattern: str, search_path: Optional[str] = None) -> str:
    """执行 glob 文件匹配"""
    # 安全检查
    safe, msg = is_safe_path(root_dir, search_path)
    if not safe:
        return f"[安全拦截] {msg}"
    
    # 确定搜索目录
    if search_path:
        search_dir = (root_dir / search_path).resolve()
    else:
        search_dir = root_dir
    
    # 检查路径是否存在
    if not search_dir.exists():
        return f"[错误] 路径不存在: {search_path or '.'}"
    
    if not search_dir.is_dir():
        return f"[错误] 路径不是目录: {search_path or '.'}"
    
    try:
        # 使用 pathlib 进行 glob 匹配
        matched_files = list(search_dir.glob(pattern))
        
        # 过滤只保留文件（不包含目录）
        matched_files = [f for f in matched_files if f.is_file()]
        
        # 按修改时间排序（最新的在前）
        matched_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not matched_files:
            return f"[结果] 未找到匹配模式 '{pattern}' 的文件"
        
        # 构建输出
        output_lines = [f"[结果] 找到 {len(matched_files)} 个匹配文件（按修改时间排序）:"]
        output_lines.append("")
        
        for file_path in matched_files:
            # 计算相对路径
            try:
                rel_path = file_path.relative_to(root_dir)
                output_lines.append(str(rel_path))
            except ValueError:
                output_lines.append(str(file_path))
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"[错误] 文件匹配失败: {str(e)}"


def create_glob_tool(base_dir: Path) -> BaseTool:
    """创建 Glob 文件模式匹配工具"""
    root_dir = (base_dir / "workspace").resolve()
    
    def glob_func(
        pattern: str,
        path: Optional[str] = None
    ) -> str:
        """Glob 文件匹配入口函数"""
        if not pattern:
            return "[错误] pattern 不能为空"
        
        return glob_files(
            root_dir=root_dir,
            pattern=pattern,
            search_path=path
        )
    
    return StructuredTool.from_function(
        name="glob",
        description=f"""按文件名模式查找文件 - 快速定位特定类型文件。

【适用场景】
- 查找所有特定类型的文件（如所有 Python 文件）
- 查找测试文件（如 `*.test.py`）
- 查找配置文件（如 `*.config.js`）
- 知道文件类型但不知道具体位置

【不适用场景】
- 按内容搜索（用 grep）
- 浏览目录结构（用 list_workspace）
- 模糊语义搜索（用 search_codebase）

【工作目录】 {base_dir / "workspace"}

【参数】
- pattern (字符串, 必需): glob 模式
  示例: "**/*.py"        # 所有 Python 文件
  示例: "src/**/*.ts"    # src 目录下的 TypeScript
  示例: "*.{{ts,tsx}}"   # TS 和 TSX 文件
  示例: "**/*.test.*"    # 所有测试文件

- path (字符串, 可选): 搜索起始目录（相对路径）

【常用模式】
┌──────────────────┬────────────────────────────┐
│ 模式             │ 描述                       │
├──────────────────┼────────────────────────────┤
│ **/*.py          │ 所有 Python 文件           │
│ src/**/*.ts      │ src 下的 TypeScript        │
│ *.{{ts,tsx}}     │ TS 和 TSX 文件             │
│ **/*.test.*      │ 所有测试文件               │
│ **/*.config.*    │ 所有配置文件               │
│ **/*.md          │ 所有 Markdown 文件         │
└──────────────────┴────────────────────────────┘

【使用示例】
1. 查找所有 Python 文件:
   pattern="**/*.py"

2. 查找 src 目录下的组件:
   pattern="**/*.vue"
   path="src"

【搜索工具选择】
┌─────────────────────┬─────────────────────┬─────────────────────────┐
│      场景           │     推荐工具        │         原因            │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ 找某类型文件        │ glob               │ 按文件名模式匹配        │
│ 知道函数/变量名     │ grep               │ 按内容精确匹配          │
│ 模糊概念/语义       │ search_codebase    │ 理解意图搜索            │
│ 浏览目录结构        │ list_workspace     │ 目录树展示              │
└─────────────────────┴─────────────────────┴─────────────────────────┘
""",
        func=glob_func,
        args_schema=GlobInput
    )
