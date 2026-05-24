"""工具注册工厂"""
from pathlib import Path
from typing import List
from langchain_core.tools import BaseTool

from .terminal_tool import create_terminal_tool
from .python_repl_tool import create_python_repl_tool
from .fetch_url_tool import create_fetch_url_tool
from .read_file_tool import create_read_file_tool
from .search_knowledge_tool import create_search_knowledge_tool
from .todo_tool import create_todo_tool
from .write_file_tool import create_write_file_tool
from .apply_diff_tool import create_apply_diff_tool
from .edit_file_tool import create_edit_file_tool
from .list_workspace_tool import create_list_workspace_tool
from .grep_tool import create_grep_tool
from .glob_tool import create_glob_tool
from .search_codebase_tool import create_search_codebase_tool
from .finish_tool import create_finish_tool


def get_all_tools(base_dir: Path) -> List[BaseTool]:
    """获取所有核心工具"""
    return [
        create_terminal_tool(base_dir),
        create_python_repl_tool(),
        create_fetch_url_tool(),
        create_read_file_tool(base_dir),
        create_search_knowledge_tool(base_dir),
        create_todo_tool(base_dir),
        create_write_file_tool(base_dir),
        create_apply_diff_tool(base_dir),
        create_edit_file_tool(base_dir),
        create_list_workspace_tool(base_dir),
        create_grep_tool(base_dir),
        create_glob_tool(base_dir),
        create_search_codebase_tool(base_dir),
        create_finish_tool(base_dir),
    ]
