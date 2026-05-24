"""日志工具模块 - 支持控制台和文件双重输出，带颜色区分"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


# 颜色代码
class Colors:
    """终端颜色代码"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # 日志级别颜色
    DEBUG = '\033[36m'      # 青色
    INFO = '\033[32m'       # 绿色
    WARNING = '\033[33m'    # 黄色
    ERROR = '\033[31m'      # 红色
    CRITICAL = '\033[35m'   # 紫色
    
    # 其他颜色
    GRAY = '\033[90m'       # 灰色（用于次要信息）
    BLUE = '\033[34m'       # 蓝色


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.DEBUG,
        logging.INFO: Colors.INFO,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.ERROR,
        logging.CRITICAL: Colors.CRITICAL,
    }
    
    def __init__(self, fmt: str, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        # 保存原始级别名称
        original_levelname = record.levelname
        
        if self.use_colors and sys.stdout.isatty():
            # 添加颜色
            color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
            record.levelname = f"{color}{Colors.BOLD}{record.levelname}{Colors.RESET}"
            
            # 为不同级别添加图标
            icons = {
                logging.DEBUG: "🔍",
                logging.INFO: "ℹ️",
                logging.WARNING: "⚠️",
                logging.ERROR: "❌",
                logging.CRITICAL: "🚨",
            }
            record.msg = f"{icons.get(record.levelno, '')} {record.msg}"
        
        result = super().format(record)
        record.levelname = original_levelname
        return result


class QuietInfoFilter(logging.Filter):
    """过滤器：正常流程的 INFO 日志只在文件输出，错误时才在控制台显示"""
    
    def __init__(self, error_keywords: Optional[list] = None):
        super().__init__()
        self.error_keywords = error_keywords or ['失败', '错误', '异常', '失败', 'error', 'exception', 'fail']
    
    def filter(self, record: logging.LogRecord) -> bool:
        # DEBUG 级别总是过滤掉（不显示在控制台）
        if record.levelno == logging.DEBUG:
            return False
        
        # WARNING 及以上级别总是显示
        if record.levelno >= logging.WARNING:
            return True
        
        # INFO 级别：检查是否包含错误关键词
        msg = str(record.getMessage()).lower()
        for keyword in self.error_keywords:
            if keyword.lower() in msg:
                return True
        
        # 正常的 INFO 日志不显示在控制台
        return False


def setup_logger(
    name: str = "Simple_agent",
    log_level: int = logging.DEBUG,
    console_level: int = logging.WARNING,  # 控制台默认只显示警告及以上
    file_level: int = logging.DEBUG,
    log_dir: Optional[Path] = None,
    quiet_info: bool = True  # 是否启用安静模式（正常INFO不显示在控制台）
) -> logging.Logger:
    """配置日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 全局日志级别
        console_level: 控制台输出级别
        file_level: 文件输出级别
        log_dir: 日志文件存放目录，默认为 backend/logs
        quiet_info: 是否启用安静模式，正常流程的INFO只在文件记录
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 文件日志格式（无颜色）
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台日志格式（带颜色）
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        use_colors=True
    )
    
    # 1. 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    if quiet_info:
        # 安静模式：使用过滤器，正常INFO不显示
        console_handler.addFilter(QuietInfoFilter())
        console_handler.setLevel(logging.DEBUG)  # 过滤器会处理级别
    else:
        console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 2. 文件输出（自动轮转，最多保留5个备份，每个10MB）
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


# 全局日志记录器实例
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称，建议使用模块名或类名
        
    Returns:
        配置好的日志记录器
    """
    return logging.getLogger(f"Simple_agent.{name}")


# 便捷函数
def debug(msg: str, *args, **kwargs):
    """调试级别日志（仅文件）"""
    logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """信息级别日志（正常流程不显示在控制台，错误时显示）"""
    logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """警告级别日志（控制台+文件，黄色）"""
    logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """错误级别日志（控制台+文件，红色）"""
    logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """严重错误级别日志（控制台+文件，紫色）"""
    logger.critical(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs):
    """异常级别日志（自动包含堆栈信息）"""
    logger.exception(msg, *args, **kwargs)
