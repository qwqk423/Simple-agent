"""Python 代码解释器"""
import io
import sys
from pathlib import Path
from typing import Any, Dict, Union
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from utils.logger import get_logger

logger = get_logger("PythonREPLTool")


def execute_python_code(code: str) -> str:
    """执行 Python 代码并返回结果"""
    code = code.strip()
    if not code:
        logger.warning("Python 代码为空")
        return "[错误] 代码不能为空"

    logger.debug(f"执行 Python 代码: {code[:100]}{'...' if len(code) > 100 else ''}")

    # 创建一个隔离的命名空间
    namespace = {
        "__builtins__": __builtins__,
    }

    # 尝试作为表达式执行
    try:
        result = eval(code, namespace)
        result_str = repr(result)
        logger.info(f"Python 表达式执行成功，结果类型: {type(result).__name__}")
        return f"结果: {result_str[:500]}{'...' if len(result_str) > 500 else ''}"
    except SyntaxError:
        # 不是表达式，作为语句执行
        pass
    except Exception as e:
        logger.error(f"Python 表达式执行失败: {type(e).__name__}: {e}")
        return f"[错误] {type(e).__name__}: {str(e)}"

    # 作为语句执行
    # 捕获标准输出以获取 print() 输出
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()

    try:
        exec(code, namespace)
        # 获取捕获的输出
        output = captured_output.getvalue()
        if output:
            logger.info(f"Python 代码执行成功，输出长度: {len(output)}")
            return output.rstrip()[:2000] + ('...' if len(output) > 2000 else '')
        else:
            logger.info("Python 代码执行成功，无输出")
            return "[代码执行完成，无输出]"
    except Exception as e:
        logger.error(f"Python 代码执行失败: {type(e).__name__}: {e}")
        return f"[错误] {type(e).__name__}: {str(e)}"
    finally:
        sys.stdout = old_stdout


class PythonREPLInput(BaseModel):
    """Python REPL 工具的输入参数"""
    code: str = Field(description="要执行的 Python 代码")

def create_python_repl_tool() -> BaseTool:
    """创建 Python REPL 工具"""

    def python_func(code: str) -> str:
        """执行 Python 代码"""
        if not code or not code.strip():
            logger.warning("Python 代码为空")
            return "[错误] 代码不能为空"

        logger.debug(f"Python REPL 工具调用")
        return execute_python_code(code)
    
    return StructuredTool.from_function(
        name="python_repl",
        description="""执行 Python 代码 - 计算、数据处理、脚本执行。

【适用场景】
- 数值计算和数据分析
- 字符串/数据处理
- 验证代码逻辑
- 快速原型测试

【参数】
- code (字符串, 必需): 要执行的 Python 代码

【返回】
- print() 的输出
- 表达式的返回值

【支持】
- Python 标准库
- 常见第三方库（numpy, pandas 等）

【注意】
代码在隔离环境中执行，每次调用独立
""",
        func=python_func,
        args_schema=PythonREPLInput
    )
