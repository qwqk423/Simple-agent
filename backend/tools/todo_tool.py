"""待办事项管理工具 - 统一的任务列表读写管理"""
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Union, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

from utils.logger import get_logger

logger = get_logger("TodoTool")


# 状态常量
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"

VALID_STATUSES = [STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_BLOCKED]
VALID_PRIORITIES = ["high", "medium", "low"]

STATUS_ICONS = {
    STATUS_PENDING: "□",
    STATUS_IN_PROGRESS: "◐",
    STATUS_COMPLETED: "✓",
    STATUS_BLOCKED: "⚠"
}

STATUS_LABELS = {
    STATUS_PENDING: "待处理",
    STATUS_IN_PROGRESS: "进行中",
    STATUS_COMPLETED: "已完成",
    STATUS_BLOCKED: "被阻塞"
}

PRIORITY_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低"
}

# 当前会话ID（由 agent.py 设置）
_current_session_id: Optional[str] = None


def set_current_session_id(session_id: str):
    """设置当前会话ID（由 Agent 调用）"""
    global _current_session_id
    _current_session_id = session_id


def get_current_session_id() -> str:
    """获取当前会话ID"""
    return _current_session_id or "default"


class TodoItem(BaseModel):
    """单个待办事项"""
    title: str = Field(description="任务标题/描述")
    status: str = Field(default="pending", description="状态: pending | in_progress | completed | blocked")


class TodoInput(BaseModel):
    """待办事项工具的输入参数"""
    todos: List[TodoItem] = Field(description="完整的待办事项列表，会替换当前列表")


def get_todo_file_path(conversation_id: str = "default") -> Path:
    """获取待办事项文件路径
    
    Args:
        conversation_id: 对话ID，用于区分不同对话的任务列表
    """
    tools_dir = Path(__file__).parent
    return tools_dir / ".todo_list" / f"{conversation_id}_todos.json"


def load_todos(conversation_id: str = "default") -> List[Dict[str, Any]]:
    """加载待办事项列表
    
    Args:
        conversation_id: 对话ID，用于区分不同对话的任务列表
    """
    todo_file = get_todo_file_path(conversation_id)
    if todo_file.exists():
        try:
            with open(todo_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_todos(todos: List[Dict[str, Any]], conversation_id: str = "default") -> None:
    """保存待办事项列表
    
    Args:
        todos: 待办事项列表
        conversation_id: 对话ID，用于区分不同对话的任务列表
    """
    todo_file = get_todo_file_path(conversation_id)
    todo_file.parent.mkdir(parents=True, exist_ok=True)
    with open(todo_file, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def validate_todos(todos: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
    """验证待办事项列表"""
    if not isinstance(todos, list):
        return False, "todos 必须是一个数组"
    
    # 检查是否有重复ID
    ids = [item.get("id") for item in todos if item.get("id")]
    if len(ids) != len(set(ids)):
        return False, "存在重复的任务ID"
    
    # 检查是否只有一个 in_progress
    in_progress_count = sum(1 for item in todos if item.get("status") == STATUS_IN_PROGRESS)
    if in_progress_count > 1:
        return False, "同时只能有一个任务处于 in_progress 状态"
    
    for i, item in enumerate(todos):
        if not item.get("title"):
            return False, f"第 {i+1} 个任务缺少标题"
        if item.get("status") not in VALID_STATUSES:
            return False, f"第 {i+1} 个任务状态无效: {item.get('status')}"
    
    return True, None


def format_todos(todos: List[Dict[str, Any]], show_summary: bool = True) -> str:
    """格式化待办事项列表为可读字符串"""
    if not todos:
        return "📋 当前没有待办事项"
    
    lines = []
    
    # 统计信息
    if show_summary:
        total = len(todos)
        completed = sum(1 for item in todos if item.get("status") == STATUS_COMPLETED)
        in_progress = sum(1 for item in todos if item.get("status") == STATUS_IN_PROGRESS)
        pending = sum(1 for item in todos if item.get("status") == STATUS_PENDING)
        blocked = sum(1 for item in todos if item.get("status") == STATUS_BLOCKED)
        progress = round(completed / total * 100, 0) if total > 0 else 0
        
        lines.append(f"📋 任务进度: {completed}/{total} ({progress:.0f}%)")
        lines.append(f"   进行中: {in_progress} | 待处理: {pending} | 被阻塞: {blocked} | 已完成: {completed}")
        lines.append("")
    
    # 按状态排序：进行中 > 被阻塞 > 待处理 > 已完成
    status_order = {
        STATUS_IN_PROGRESS: 0,
        STATUS_BLOCKED: 1,
        STATUS_PENDING: 2,
        STATUS_COMPLETED: 3
    }
    sorted_todos = sorted(todos, key=lambda x: status_order.get(x.get("status"), 99))
    
    for item in sorted_todos:
        status = item.get("status", STATUS_PENDING)
        title = item.get("title", "")
        todo_id = item.get("id", "")[:6]  # 短ID
        
        icon = STATUS_ICONS.get(status, "□")
        lines.append(f"{icon} {title} (ID: {todo_id})")
    
    return "\n".join(lines)


def generate_id() -> str:
    """生成短ID"""
    return uuid.uuid4().hex[:8]


def todo_tool_logic(todos_input: List[Any], conversation_id: str = "default") -> str:
    """
    核心逻辑：更新整个待办事项列表
    
    流程：
    1. 为没有ID的任务生成ID
    2. 验证任务列表
    3. 保存到文件（按对话ID隔离）
    4. 返回格式化后的列表
    
    Args:
        todos_input: 待办事项列表（可以是Dict或TodoItem）
        conversation_id: 对话ID，用于区分不同对话的任务列表
    """
    try:
        # 处理输入，确保格式正确
        processed_todos = []
        seen_titles = set()  # 用于去重
        
        for item in todos_input:
            # 支持 Dict 和 Pydantic Model
            if hasattr(item, 'dict'):
                # Pydantic v1
                item_dict = item.dict()
            elif hasattr(item, 'model_dump'):
                # Pydantic v2
                item_dict = item.model_dump()
            else:
                # Dict
                item_dict = item
            
            title = item_dict.get("title", "").strip()
            
            # 去重：相同标题只保留第一个
            if title in seen_titles:
                logger.debug(f"跳过重复任务: {title}")
                continue
            seen_titles.add(title)
            
            todo = {
                "id": item_dict.get("id") or generate_id(),
                "title": title,
                "status": item_dict.get("status", STATUS_PENDING)
            }
            processed_todos.append(todo)
        
        # 限制任务数量（最多20个）
        if len(processed_todos) > 20:
            logger.warning(f"任务数量过多({len(processed_todos)})，截断至20个")
            processed_todos = processed_todos[:20]
        
        # 验证
        valid, msg = validate_todos(processed_todos)
        if not valid:
            return f"[错误] {msg}"
        
        # 保存（按对话ID隔离）
        save_todos(processed_todos, conversation_id)
        
        # 返回格式化结果
        return format_todos(processed_todos, show_summary=True)
        
    except Exception as e:
        return f"[错误] 操作失败: {str(e)}"


def create_todo_tool(base_dir: Path) -> BaseTool:
    """创建待办事项管理工具（读写合一）
    
    Args:
        base_dir: 基础目录
    """
    
    def todo_func(todos: List[Dict[str, str]]) -> str:
        """
        更新待办事项列表，并返回当前状态。
        传入完整的列表会替换现有列表，用于创建、更新、完成任务。
        自动使用当前对话的 session_id。
        """
        if not isinstance(todos, list):
            return "[错误] todos 必须是一个数组"
        
        # 自动获取当前会话ID
        session_id = get_current_session_id()
        return todo_tool_logic(todos, session_id)
    
    return StructuredTool.from_function(
        name="set_todo_list",
        description="""管理待办事项列表 - 跟踪任务进度。

【功能】
- 创建任务列表
- 更新任务状态
- 查看进度统计

【参数】
- todos (数组, 必需): 完整任务列表，每项包含:
  - title (字符串, 必需): 任务描述
  - status (字符串, 可选): pending(待处理) | in_progress(进行中) | completed(已完成) | blocked(阻塞)
  - id (字符串, 可选): 任务ID，自动生成

【使用场景】
- 复杂任务：开始前创建列表，跟踪进度
- 多步骤任务：标记每步完成状态

【示例】
todos=[
  {"title": "分析需求", "status": "completed"},
  {"title": "编写代码", "status": "in_progress"},
  {"title": "测试验证", "status": "pending"}
]

【重要规则】
- 只能有一个 in_progress 任务
- ⚠️ 每次调用会【完全替换】现有列表，不是追加！
- 更新任务时：先读取当前列表，修改后再完整传回
- 任务列表按对话隔离

【正确用法】
1. 首次创建：todos=[{任务1}, {任务2}, {任务3}]
2. 更新状态：先获取现有列表 → 修改状态 → 完整传回所有任务
3. 不要重复创建相同任务，不要累积过多任务（建议最多10个）
""",
        func=todo_func,
        args_schema=TodoInput
    )
