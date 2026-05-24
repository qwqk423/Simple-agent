"""命令行操作工具 - 沙箱终端（自动适配 Windows/Linux/macOS）"""
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from utils.logger import get_logger

logger = get_logger("TerminalTool")

# ============================================================
# 运行时环境检测（模块加载时执行一次）
# ============================================================
_SYSTEM = platform.system()

if _SYSTEM == "Windows":
    _pwsh = shutil.which("pwsh")       # PowerShell 7+
    _ps5 = shutil.which("powershell") or shutil.which("powershell.exe")
    if _pwsh:
        _SHELL_TYPE = "pwsh"
        _SHELL_PATH = _pwsh
    elif _ps5:
        _SHELL_TYPE = "powershell"
        _SHELL_PATH = _ps5
    else:
        _SHELL_TYPE = "cmd"
        _SHELL_PATH = os.environ.get("COMSPEC", "cmd.exe")
else:
    _SHELL_TYPE = "bash"
    _SHELL_PATH = "/bin/bash"

logger.info(f"终端工具环境: system={_SYSTEM}, shell={_SHELL_TYPE}, path={_SHELL_PATH}")


# ============================================================
# 高危命令黑名单
# ============================================================
BLACKLISTED_COMMANDS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+/\s*",
    r"Remove-Item\s+-Recurse\s+-Force\s+C:\\",
    r"del\s+/F\s+/S\s+C:\\",
    r"mkfs",
    r"dd\s+if=.*of=/dev/",
    r"shutdown",
    r"reboot",
    r"halt",
    r":\(\)\s*\{\s*:\|\:&\s*\};\s*:",  # fork bomb
    r">\s*/dev/",
    r"curl\s+.*\s*\|\s*sh",  # 管道到shell
    r"wget\s+.*\s*\|\s*sh",
    r"Stop-Computer",
    r"Restart-Computer",
]


def is_command_safe(command: str) -> tuple[bool, Optional[str]]:
    """检查命令是否安全"""
    for pattern in BLACKLISTED_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            logger.warning(f"高危命令被拦截: {command[:100]}..., 匹配模式: {pattern}")
            return False, f"命令包含高危操作，已被拦截: {pattern}"
    return True, None


# ============================================================
# 命令执行
# ============================================================
def _decode_output(data: bytes) -> str:
    """尝试多种编码解码输出"""
    if not data:
        return ""
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1', 'cp936']
    for enc in encodings:
        try:
            return data.decode(enc, errors='strict')
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode('utf-8', errors='replace')


def execute_command(commands: Union[str, list], root_dir: Optional[Path] = None) -> str:
    """执行命令（自动适配当前 OS Shell）"""
    if isinstance(commands, list):
        commands = " ".join(str(c) for c in commands)
    elif not isinstance(commands, str):
        commands = str(commands)

    commands = commands.strip()
    if not commands:
        logger.warning("命令为空")
        return "[错误] 命令不能为空"

    safe, msg = is_command_safe(commands)
    if not safe:
        return f"[安全拦截] {msg}"

    logger.debug(f"执行命令: {commands[:100]}{'...' if len(commands) > 100 else ''}, cwd={root_dir}")

    try:
        if _SHELL_TYPE in ("pwsh", "powershell"):
            # Windows PowerShell: 显式调用，不依赖 shell=True
            result = subprocess.run(
                [_SHELL_PATH, "-NoProfile", "-NonInteractive", "-Command", commands],
                capture_output=True,
                timeout=30,
                cwd=str(root_dir) if root_dir else None,
            )
        else:
            # Linux/macOS bash 或 Windows cmd
            result = subprocess.run(
                commands,
                shell=True,
                capture_output=True,
                timeout=30,
                cwd=str(root_dir) if root_dir else None,
            )

        logger.debug(f"命令执行完成: returncode={result.returncode}")

        stdout = _decode_output(result.stdout)
        stderr = _decode_output(result.stderr)

        output = stdout
        if stderr:
            output += "\n[stderr] " + stderr
            logger.debug(f"命令 stderr: {stderr[:200]}{'...' if len(stderr) > 200 else ''}")

        if len(output) > 5000:
            logger.debug(f"输出截断: {len(output)} -> 5000 字符")
            output = output[:5000] + "\n...[输出已截断]"

        if result.returncode != 0:
            logger.warning(f"命令返回非零状态码: {result.returncode}")

        logger.info(f"命令执行成功: {commands[:50]}{'...' if len(commands) > 50 else ''}")
        return output if output else "[命令执行完成，无输出]"

    except subprocess.TimeoutExpired:
        logger.error(f"命令执行超时 (30s): {commands[:100]}")
        return "[错误] 命令执行超时 (30s)"
    except subprocess.SubprocessError as e:
        logger.error(f"子进程错误: {type(e).__name__}: {e}")
        return f"[错误] 子进程错误: {str(e)}"
    except FileNotFoundError:
        logger.error(f"Shell 未找到: {_SHELL_PATH}")
        return f"[错误] Shell 不可用: {_SHELL_PATH}"
    except Exception as e:
        logger.error(f"命令执行失败: {type(e).__name__}: {e}")
        return f"[错误] {str(e)}"


# ============================================================
# 工具定义
# ============================================================
class TerminalInput(BaseModel):
    """终端工具的输入参数"""
    commands: str = Field(description="要执行的命令字符串，如 'ls -la', 'mkdir test_dir'")


def _build_description(base_dir: Path, workspace_dir: Path) -> str:
    """根据 OS 生成动态工具描述"""
    if _SHELL_TYPE in ("pwsh", "powershell"):
        shell_note = (
            f"当前 Shell: **PowerShell**（`ls`=`Get-ChildItem`, `cat`=`Get-Content`, "
            f"`rm`=`Remove-Item`, `cp`=`Copy-Item`, `mv`=`Move-Item`，Linux 常用命令自动映射为别名）"
        )
        examples = """【使用示例】
1. 列出文件: "ls" 或 "Get-ChildItem"
2. 查看文件: "cat README.md" 或 "Get-Content README.md"
3. 创建目录: "mkdir new_folder" 或 "New-Item -ItemType Directory new_folder"
4. 删除文件: "rm old_file.txt" 或 "Remove-Item old_file.txt"
5. 复制文件: "cp a.txt b.txt" 或 "Copy-Item a.txt b.txt"
6. 安装依赖: "cd backend && pip install -r requirements.txt"
7. 检查进程: "Get-Process python" """
    else:
        shell_note = f"当前 Shell: **Bash**"
        examples = """【使用示例】
1. 列出文件: "ls -la"
2. 查看文件: "cat README.md"
3. 创建目录: "mkdir -p new_folder"
4. 删除文件: "rm old_file.txt"
5. 复制文件: "cp a.txt b.txt"
6. 安装依赖: "cd backend && pip install -r requirements.txt" """

    return f"""执行 Shell 命令 - 系统操作和文件管理。

【当前环境】
- 操作系统: {_SYSTEM}
- Shell: {_SHELL_TYPE}
- 工作目录: {workspace_dir}
{shell_note}

【适用场景】
- 执行系统命令
- 运行构建脚本（npm install, pip install 等）
- 查看系统信息
- 批量文件操作

【参数格式 - 重要】
- commands: 字符串格式，完整命令行
  ✅ 正确: "ls -la"
  ✅ 正确: "cd code && npm install"
  ❌ 错误: ["ls", "-la"]  （不要传数组）
  ❌ 错误: {{"command": "ls"}}  （不要传对象）

【限制】
- 30秒超时
- 输出最多5000字符
- 高危命令会被拦截

{examples}

【安全提示】
- 谨慎使用删除命令
- 避免执行不信任的脚本
"""


def create_terminal_tool(base_dir: Path) -> BaseTool:
    """创建终端工具（自动适配当前 OS）"""
    workspace_dir = (base_dir / "workspace").resolve()
    logger.debug(f"终端工具工作目录: {workspace_dir}, shell: {_SHELL_TYPE}")

    def terminal_func(commands: str) -> str:
        """执行 shell 命令"""
        if not commands or not commands.strip():
            logger.warning("命令为空")
            return "[错误] 命令不能为空"

        logger.debug(f"终端工具调用: workspace={workspace_dir}")
        return execute_command(commands, root_dir=workspace_dir)

    description = _build_description(base_dir, workspace_dir)

    return StructuredTool.from_function(
        name="terminal",
        description=description,
        func=terminal_func,
        args_schema=TerminalInput,
    )