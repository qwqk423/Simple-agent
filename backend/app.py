"""FastAPI 应用入口"""
import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import init_config_manager
from graph.agent import agent_manager
from tools.skills_scanner import scan_and_generate_snapshot
from graph.memory_indexer import get_memory_indexer
from utils.logger import get_logger

logger = get_logger("App")

# 先初始化配置管理器（必须在导入 API 路由之前）
try:
    init_config_manager(BASE_DIR)
    logger.info("配置管理器初始化完成")
except Exception as e:
    logger.critical(f"配置管理器初始化失败，应用无法启动: {e}")
    raise

# 导入 API 路由
from api import chat, sessions, files, tokens, compress, config_api


def initialize_app():
    """应用初始化（同步版本，供异步包装调用）"""
    logger.info("=" * 50)
    logger.info("Simple Agent 初始化中...")
    logger.info("=" * 50)

    # 1. 配置管理器已在导入前初始化
    logger.info("[1/4] 配置管理器已就绪")

    # 2. 扫描技能
    try:
        scan_and_generate_snapshot(BASE_DIR)
        logger.info("[2/4] 技能扫描完成")
    except Exception as e:
        logger.error(f"[2/4] 技能扫描失败: {e}")
        raise

    # 3. 初始化 Agent 管理器
    try:
        agent_manager.initialize(BASE_DIR)
        logger.info("[3/4] Agent 管理器初始化完成")
    except Exception as e:
        logger.error(f"[3/4] Agent 管理器初始化失败: {e}")
        raise

    # 4. 构建记忆索引（如果已有有效索引则跳过）
    try:
        indexer = get_memory_indexer(BASE_DIR)
        if indexer.load_index():
            logger.info("[4/4] 记忆索引加载完成（已存在）")
        else:
            indexer.rebuild_index()
            logger.info("[4/4] 记忆索引构建完成")
    except Exception as e:
        logger.error(f"[4/4] 记忆索引初始化失败: {e}")
        raise

    logger.info("=" * 50)
    logger.info("Simple Agent 启动成功！")
    logger.info(f"API 地址: http://localhost:8080")
    logger.info("=" * 50)


# 初始化超时时间（秒）
INITIALIZATION_TIMEOUT = 120


async def initialize_app_with_timeout():
    """应用初始化（带超时控制）"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        try:
            await asyncio.wait_for(
                loop.run_in_executor(executor, initialize_app),
                timeout=INITIALIZATION_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.critical(f"应用初始化超时（>{INITIALIZATION_TIMEOUT}秒）")
            raise RuntimeError(f"应用初始化超时，请检查相关服务状态")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    try:
        await initialize_app_with_timeout()
    except Exception as e:
        logger.critical(f"应用初始化失败: {e}")
        raise
    try:
        yield
    except Exception as e:
        # yield 期间的异常也需要记录，但不影响关闭流程
        logger.error(f"应用运行期间发生异常: {e}")
        raise
    finally:
        # 关闭时清理（确保无论如何都会执行）
        try:
            logger.info("Simple Agent 关闭中...")
        except Exception as e:
            # 确保关闭日志的异常不会掩盖原始异常
            print(f"关闭日志记录失败: {e}")


# 创建 FastAPI 应用
app = FastAPI(
    title="Simple Agent API",
    description="轻量级、全透明的 AI Agent 系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(tokens.router, prefix="/api")
app.include_router(compress.router, prefix="/api")
app.include_router(config_api.router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    logger.debug("访问根路径 /")
    return {
        "name": "Simple Agent",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    logger.debug("健康检查请求 /health")
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    logger.info("启动 Uvicorn 服务器...")
    try:
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8080,
            reload=True
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，服务器停止")
    except Exception as e:
        logger.critical(f"服务器启动失败: {e}")
        raise
