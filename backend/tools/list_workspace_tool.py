"""工作区目录列表工具 - 列出给定路径中的文件和目录"""
import fnmatch
import os
from pathlib import Path
from typing import Dict, Any, Union, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool


# 默认忽略列表（内置，不暴露给 LLM）
DEFAULT_IGNORES = [
    "node_modules",
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
]

# 最大返回条目数
MAX_ENTRIES = 200


def is_safe_path(root_dir: Path, target_path: str) -> tuple[bool, Optional[str]]:
    """安全检查（通用函数，可复用）"""
    try:
        target = (root_dir / target_path).resolve()
        target.relative_to(root_dir)
    except ValueError:
        return False, "路径逃逸检测: 禁止访问项目目录外的文件"
    
    if ".." in target_path or "~" in target_path:
        return False, "路径包含非法字符"
    
    return True, None


def should_ignore(file_path: Path, ignore_patterns: List[str]) -> bool:
    """检查文件是否应该被忽略"""
    path_str = str(file_path)
    name = file_path.name
    
    for pattern in ignore_patterns:
        # 匹配文件名
        if fnmatch.fnmatch(name, pattern):
            return True
        # 匹配完整路径
        if fnmatch.fnmatch(path_str, pattern):
            return True
        # 匹配路径中的某一部分
        if pattern in path_str.split(os.sep):
            return True
    
    return False


def list_directory(
    root_dir: Path,
    target_path: str,
    glob_pattern: Optional[str] = None,
    custom_ignores: Optional[List[str]] = None
) -> str:
    """
    核心逻辑实现：列出目录内容
    """
    # 安全检查
    safe, msg = is_safe_path(root_dir, target_path)
    if not safe:
        return f"[安全拦截] {msg}"
    
    try:
        target = (root_dir / target_path).resolve()
        
        # 检查路径是否存在
        if not target.exists():
            return f"[错误] 路径不存在: {target_path}"
        
        if not target.is_dir():
            return f"[错误] 路径不是目录: {target_path}"
        
        # 合并忽略模式（默认 + 自定义）
        ignore_patterns = DEFAULT_IGNORES.copy()
        if custom_ignores:
            ignore_patterns.extend(custom_ignores)
        
        entries = []
        total_count = 0
        truncated = False
        
        # 遍历目录
        for item in target.iterdir():
            total_count += 1
            
            # 检查是否应该忽略
            if should_ignore(item, ignore_patterns):
                continue
            
            # 检查 glob 模式匹配
            if glob_pattern and not fnmatch.fnmatch(item.name, glob_pattern):
                continue
            
            entries.append(item)
        
        # 排序：目录在前，文件在后，然后按名称排序
        entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        
        # 检查是否超过最大条目数
        if len(entries) > MAX_ENTRIES:
            entries = entries[:MAX_ENTRIES]
            truncated = True
        
        # 格式化输出
        lines = []
        lines.append(f"目录: {target_path}")
        lines.append("")
        
        if not entries:
            lines.append("(空目录或所有条目被忽略)")
        else:
            for entry in entries:
                prefix = "📁 " if entry.is_dir() else "📄 "
                lines.append(f"{prefix}{entry.name}")
        
        if truncated:
            lines.append("")
            lines.append(f"[提示] 结果已截断，仅显示前 {MAX_ENTRIES} 个条目")
        
        lines.append("")
        lines.append(f"总计: {len(entries)} 个条目 (扫描了 {total_count} 个)")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"[错误] 列出目录失败: {str(e)}"


class ListWorkspaceInput(BaseModel):
    """工作区目录列表工具的输入参数"""
    path: str = Field(description="目录路径（相对路径，如 'src' 或 '.'）")
    glob: Optional[str] = Field(default=None, description="过滤模式，如 '*.py' 只显示Python文件")
    ignore: Optional[List[str]] = Field(default=None, description="额外忽略的文件名模式")

def create_list_workspace_tool(base_dir: Path) -> BaseTool:
    """创建工作区目录列表工具（工厂函数）"""
    root_dir = (base_dir / "workspace").resolve()
    
    def list_func(path: str, glob: Optional[str] = None, ignore: Optional[List[str]] = None) -> str:
        """工具入口函数"""
        if not path:
            return "[错误] path 不能为空"
        
        if not Path(path).is_absolute():
            path = str(Path(root_dir) / path)
        
        return list_directory(root_dir, path, glob, ignore)
    
    return StructuredTool.from_function(
        name="list_workspace",
        description=f"""列出目录中的文件和子目录，浏览项目结构。

【适用场景】
- 初次接触项目，了解目录结构
- 查找某个目录下有哪些文件
- 验证文件是否存在

【不适用场景】
- 按文件名模式查找（用 glob 更高效）
- 搜索代码内容（用 grep 或 search_codebase）

【工作目录】 {base_dir / "workspace"}

【参数】
- path (字符串, 必需): 目录路径（相对路径，如 "src" 或 "."）
- glob (字符串, 可选): 过滤模式，如 "*.py" 只显示Python文件
- ignore (数组, 可选): 额外忽略的文件名模式

【输出特点】
- 目录用 📁 标识，文件用 📄 标识
- 按名称排序，目录在前
- 自动忽略 node_modules, .git, __pycache__ 等
- 最多返回200个条目

【工具对比】
- list_workspace: 浏览目录内容，了解结构
- glob: 按模式搜索文件，返回完整路径列表
- read_file: 读取具体文件内容
""",
        func=list_func,
        args_schema=ListWorkspaceInput
    )
