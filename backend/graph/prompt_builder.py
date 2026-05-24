"""System Prompt 组装器"""
import os
import platform
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import tiktoken

from utils.logger import get_logger

logger = get_logger("PromptBuilder")

# Token 限制
MAX_FILE_CHARS = 20000  # 单文件字符限制

# 延迟初始化 encoding，避免模块导入时失败
def _get_encoding():
    """获取 tiktoken encoding（延迟初始化）"""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        logger.error(f"加载 tiktoken encoding 失败: {e}")
        return None


# 全局 encoding 实例（延迟初始化）
_ENCODING = None


def _ensure_encoding():
    """确保 encoding 已初始化"""
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = _get_encoding()
    return _ENCODING


def count_tokens(text: str) -> int:
    """计算 token 数"""
    encoding = _ensure_encoding()
    if encoding is None:
        # Fallback: 使用字符数估算（约4字符/token）
        logger.warning("tiktoken encoding 不可用，使用字符数估算 token")
        return len(text) // 4
    
    try:
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"token 计算失败: {e}，使用字符数估算")
        return len(text) // 4


def truncate_text(text: str, max_chars: int = MAX_FILE_CHARS) -> str:
    """截断文本"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n...[truncated]"


def read_file_safe(path: Path) -> str:
    """安全读取文件"""
    if not path.exists():
        logger.debug(f"文件不存在: {path}")
        return ""
    try:
        content = path.read_text(encoding="utf-8")
        truncated = truncate_text(content)
        if len(truncated) < len(content):
            logger.debug(f"文件内容截断: {path} ({len(content)} -> {len(truncated)} 字符)")
        return truncated
    except UnicodeDecodeError as e:
        logger.warning(f"文件编码错误 [{path}]: {e}")
        return f"[读取失败: 编码错误 {e}]"
    except PermissionError as e:
        logger.warning(f"读取文件权限不足 [{path}]: {e}")
        return f"[读取失败: 权限不足 {e}]"
    except Exception as e:
        logger.error(f"读取文件失败 [{path}]: {e}")
        return f"[读取失败: {e}]"


class PromptBuilder:
    """System Prompt 构建器"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.workspace_dir = base_dir / "workspace"
        logger.debug(f"PromptBuilder初始化: base_dir={base_dir}")
    
    def _detect_environment(self) -> str:
        """检测当前运行环境"""
        system = platform.system()
        if system == "Windows":
            os_name = f"Windows {platform.release()}"
            shell = os.environ.get("SHELL", os.environ.get("COMSPEC", "powershell"))
            home = os.environ.get("USERPROFILE", "~")
        elif system == "Darwin":
            os_name = f"macOS {platform.mac_ver()[0]}"
            shell = os.environ.get("SHELL", "/bin/zsh")
            home = os.environ.get("HOME", "~")
        else:
            os_name = f"Linux {platform.release()}"
            shell = os.environ.get("SHELL", "/bin/bash")
            home = os.environ.get("HOME", "~")

        return (
            f"## 当前环境\n"
            f"- 操作系统: {os_name}\n"
            f"- 系统类型: {system}\n"
            f"- Shell: {shell}\n"
            f"- 用户目录: {home}\n"
            f"- Python: {sys.version.split()[0]}\n"
            f"- 工作目录: {self.workspace_dir}"
        )

    def build_system_prompt(self, rag_mode: bool = False, thinking_enabled: bool = True) -> str:
        """构建完整的 System Prompt

        Args:
            rag_mode: 是否启用 RAG 模式（当前未使用，预留参数）
            thinking_enabled: 是否启用思考模式（当前未使用，预留参数）

        TODO: 实现 rag_mode 和 thinking_enabled 参数的功能
        """
        parts = []

        # ① 环境检测（放在最前面，让 AI 第一时间了解运行环境）
        env_info = self._detect_environment()
        parts.append(env_info)

        # ② AGENTS.md
        agents = self.workspace_dir / "AGENTS.md"
        content = read_file_safe(agents)
        if content:
            parts.append(f"<!-- Agents Guide -->\n{content}")
            logger.debug(f"AGENTS.md已加载: {len(content)} 字符")
        else:
            logger.warning(f"AGENTS.md为空或不存在: {agents}")
        
        result = "\n\n".join(parts)
        logger.debug(f"System Prompt构建完成: {len(result)} 字符")
        return result
    
    def get_file_tokens(self, relative_path: str) -> Dict[str, Any]:
        """获取文件的 token 统计"""
        path = self.base_dir / relative_path
        if not path.exists():
            return {"path": relative_path, "exists": False, "chars": 0, "tokens": 0}
        
        try:
            content = path.read_text(encoding="utf-8")
            tokens = count_tokens(content)
            return {
                "path": relative_path,
                "exists": True,
                "chars": len(content),
                "tokens": tokens
            }
        except UnicodeDecodeError as e:
            logger.warning(f"统计文件token编码错误 [{relative_path}]: {e}")
            return {"path": relative_path, "exists": True, "error": f"编码错误: {e}", "chars": 0, "tokens": 0}
        except PermissionError as e:
            logger.warning(f"统计文件token权限不足 [{relative_path}]: {e}")
            return {"path": relative_path, "exists": True, "error": f"权限不足: {e}", "chars": 0, "tokens": 0}
        except Exception as e:
            logger.error(f"统计文件token失败 [{relative_path}]: {e}")
            return {"path": relative_path, "exists": True, "error": str(e), "chars": 0, "tokens": 0}
    
    def get_all_files_tokens(self) -> Dict[str, Any]:
        """获取所有 System Prompt 组件的 token 统计"""
        files = [
            "workspace/AGENTS.md"
        ]
        
        results = []
        total_tokens = 0
        
        for f in files:
            info = self.get_file_tokens(f)
            results.append(info)
            if info.get("exists") and "tokens" in info:
                total_tokens += info["tokens"]
        
        logger.debug(f"System Prompt组件Token统计: {total_tokens} tokens")
        
        return {
            "files": results,
            "total_tokens": total_tokens
        }
