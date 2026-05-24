"""Finish 工具 - 标记会话完成"""
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool


class FinishInput(BaseModel):
    """Finish 工具的输入参数 - 可选"""
    summary: str = Field(default="", description="任务完成总结（可选）")


def finish_logic(summary: str = "") -> str:
    """核心逻辑：标记会话完成并返回总结"""
    if summary and summary.strip():
        return f"[完成] 任务已结束。总结：{summary.strip()}"
    return "[完成] 任务已结束"


def create_finish_tool(base_dir: Path) -> BaseTool:
    """创建 finish 工具（工厂函数）"""

    def finish_func(summary: str = "") -> str:
        """工具入口函数"""
        return finish_logic(summary)

    return StructuredTool.from_function(
        name="finish",
        description="""标记任务完成，立即结束当前会话。

【使用时机】
- 需要与其他工具同时调用并立即结束（省一轮往返）
- 仅工具执行就完成任务、无需额外文字回复时

【规则】
- 纯文本回复会自动结束会话，不需要显式调用此工具
- 调用后立即结束，不再执行后续工具或生成回复

【参数】
- summary (字符串, 可选): 任务完成总结
""",
        func=finish_func,
        args_schema=FinishInput
    )
