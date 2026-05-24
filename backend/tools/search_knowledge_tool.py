"""知识库搜索工具 - 使用 LlamaIndex"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter

from utils.embedding_adapter import create_openai_embedding

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from utils.logger import get_logger

logger = get_logger("SearchKnowledgeTool")


class KnowledgeBaseSearch:
    """知识库搜索器"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.knowledge_dir = base_dir / "knowledge"
        self.storage_dir = base_dir / "storage" / "knowledge_index"
        self.index: Optional[VectorStoreIndex] = None
        self.embed_model = None
        self._lock = asyncio.Lock()  # 并发锁
        self._init_embed_model()

    def _init_embed_model(self):
        """初始化 Embedding 模型（模型名称从 settings.EMBEDDING_MODEL 自动读取）"""
        try:
            from config import settings
            # 优先使用独立的 EMBEDDING_API_KEY 和 EMBEDDING_BASE_URL
            embed_api_key = settings.embedding_api_key if settings.embedding_api_key else settings.openai_api_key
            embed_base_url = settings.embedding_base_url if settings.embedding_base_url else settings.openai_base_url
            self.embed_model = create_openai_embedding(
                api_key=embed_api_key,
                base_url=embed_base_url
            )
            logger.debug("Embedding 模型初始化成功")
        except Exception as e:
            logger.error(f"Embedding 模型初始化失败: {type(e).__name__}: {e}")
            raise

    def _ensure_knowledge_dir(self):
        """确保知识库目录存在"""
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    async def build_index(self) -> bool:
        """构建知识库索引（带锁防止并发）"""
        async with self._lock:
            return self._build_index_sync()

    def _build_index_sync(self) -> bool:
        """同步构建知识库索引"""
        self._ensure_knowledge_dir()

        # 检查是否有文件
        files = list(self.knowledge_dir.glob("**/*"))
        files = [f for f in files if f.is_file() and f.suffix.lower() in [".pdf", ".md", ".txt"]]

        if not files:
            logger.debug(f"知识库目录为空，跳过索引构建: {self.knowledge_dir}")
            return False

        logger.info(f"开始构建知识库索引: {len(files)} 个文件")

        try:
            # 加载文档
            documents = SimpleDirectoryReader(
                str(self.knowledge_dir),
                required_exts=[".pdf", ".md", ".txt"]
            ).load_data()

            if not documents:
                logger.warning("知识库文档加载失败或为空")
                return False

            logger.debug(f"加载了 {len(documents)} 个文档")

            # 分割节点
            parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
            nodes = parser.get_nodes_from_documents(documents)
            logger.debug(f"分割为 {len(nodes)} 个节点")

            # 构建索引
            self.index = VectorStoreIndex(
                nodes=nodes,
                embed_model=self.embed_model
            )

            # 持久化
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.index.storage_context.persist(str(self.storage_dir))

            logger.info(f"知识库索引构建成功: {len(nodes)} 个节点")
            return True

        except Exception as e:
            logger.error(f"构建索引失败: {type(e).__name__}: {e}")
            return False

    async def load_index(self) -> bool:
        """加载已有索引（带锁防止并发）"""
        async with self._lock:
            return self._load_index_sync()

    def _load_index_sync(self) -> bool:
        """同步加载已有索引"""
        if not self.storage_dir.exists():
            logger.debug(f"索引存储目录不存在: {self.storage_dir}")
            return False

        # 检查索引文件是否完整
        required_files = ['docstore.json', 'index_store.json', 'vector_store.json']
        for f in required_files:
            if not (self.storage_dir / f).exists():
                logger.warning(f"索引文件不完整，缺少: {f}")
                return False

        try:
            storage_context = StorageContext.from_defaults(persist_dir=str(self.storage_dir))
            self.index = load_index_from_storage(
                storage_context,
                embed_model=self.embed_model
            )
            logger.info("知识库索引加载成功")
            return True
        except Exception as e:
            logger.error(f"加载索引失败: {type(e).__name__}: {e}")
            return False

    async def ensure_index(self) -> bool:
        """确保索引可用"""
        if self.index is not None:
            return True

        # 快速检查：如果知识库目录为空，直接返回False
        self._ensure_knowledge_dir()
        files = list(self.knowledge_dir.glob("**/*"))
        files = [f for f in files if f.is_file() and f.suffix.lower() in [".pdf", ".md", ".txt"]]
        if not files:
            logger.debug(f"知识库目录为空，跳过索引加载/构建: {self.knowledge_dir}")
            return False

        # 尝试加载已有索引
        if await self.load_index():
            return True

        # 构建新索引
        return await self.build_index()

    def search_sync(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """同步搜索知识库"""
        if self.index is None:
            logger.warning("搜索时索引未初始化")
            return []

        try:
            logger.debug(f"开始知识库搜索: query='{query[:50]}...', top_k={top_k}")
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)

            results = []
            for node in nodes:
                results.append({
                    "text": node.node.text,
                    "score": float(node.score) if hasattr(node, 'score') else 0.0,
                    "source": node.node.metadata.get("file_name", "unknown")
                })

            logger.info(f"知识库搜索完成: 返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"搜索失败: {type(e).__name__}: {e}")
            return []

    async def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """异步搜索知识库"""
        if not await self.ensure_index():
            logger.warning("无法确保索引可用")
            return []

        # 在线程池中执行同步搜索
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.search_sync(query, top_k))


# 按 base_dir 缓存搜索器实例
_searcher_cache: Dict[Path, KnowledgeBaseSearch] = {}


def get_searcher(base_dir: Path) -> KnowledgeBaseSearch:
    """获取搜索器实例（每个 base_dir 一个实例）"""
    global _searcher_cache
    if base_dir not in _searcher_cache:
        try:
            _searcher_cache[base_dir] = KnowledgeBaseSearch(base_dir)
            logger.debug(f"知识库搜索器创建成功: {base_dir}")
        except Exception as e:
            logger.error(f"知识库搜索器创建失败: {type(e).__name__}: {e}")
            raise
    return _searcher_cache[base_dir]


class SearchKnowledgeInput(BaseModel):
    """知识库搜索工具的输入参数"""
    query: str = Field(description="搜索关键词或问题描述")

def _is_knowledge_base_empty(base_dir: Path) -> bool:
    """快速检查知识库是否为空"""
    knowledge_dir = base_dir / "knowledge"
    if not knowledge_dir.exists():
        return True
    files = list(knowledge_dir.glob("**/*"))
    files = [f for f in files if f.is_file() and f.suffix.lower() in [".pdf", ".md", ".txt"]]
    return len(files) == 0

def create_search_knowledge_tool(base_dir: Path) -> BaseTool:
    """创建知识库搜索工具"""
    try:
        searcher = get_searcher(base_dir)
    except Exception as e:
        logger.error(f"创建知识库搜索工具失败: {e}")
        raise

    async def search_func(query: str) -> str:
        """搜索知识库"""
        if not query or not query.strip():
            logger.warning("搜索查询为空")
            return "[错误] 搜索查询不能为空"

        if _is_knowledge_base_empty(base_dir):
            logger.debug("知识库为空，跳过搜索")
            return "知识库为空，请先添加文档到 knowledge 目录。"

        logger.debug(f"知识库搜索工具调用: query='{query[:50]}...'")

        try:
            results = await searcher.search(query, top_k=3)
        except Exception as e:
            logger.error(f"知识库搜索执行失败: {type(e).__name__}: {e}")
            return f"[错误] 知识库搜索失败: {e}"

        if not results:
            logger.info("未在知识库中找到相关内容")
            return "未在知识库中找到相关内容。"

        output = []
        for i, result in enumerate(results, 1):
            output.append(f"[{i}] 来源: {result['source']} (相关度: {result['score']:.2f})")
            output.append(result['text'])
            output.append("")

        logger.info(f"知识库搜索返回 {len(results)} 个结果")
        return "\n".join(output)

    def sync_search_func(query: str) -> str:
        """同步搜索知识库"""
        import asyncio
        from concurrent.futures import TimeoutError as ConcurrentTimeoutError
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(search_func(query), loop)
                return future.result(timeout=30)
            else:
                return loop.run_until_complete(search_func(query))
        except RuntimeError:
            return asyncio.run(search_func(query))
        except (TimeoutError, ConcurrentTimeoutError):
            logger.error("知识库搜索超时 (30s)")
            return "[错误] 知识库搜索超时，请检查知识库目录是否正常"
        except Exception as e:
            logger.error(f"知识库搜索失败: {type(e).__name__}: {e}")
            return f"[错误] 知识库搜索失败: {e}"

    return StructuredTool.from_function(
        name="search_knowledge",
        description="""搜索本地知识库 - 查询文档、手册、规范等。

【适用场景】
- 查询公司内部文档
- 查找产品手册内容
- 搜索技术规范说明
- 检索PDF/MD/TXT格式的知识文档

【不适用场景 - 用 search_codebase】
- 搜索项目源代码
- 查找代码实现

【参数】
- query (字符串, 必需): 搜索关键词或问题描述

【工作原理】
基于向量检索，理解语义，不只是关键词匹配

【知识库位置】
{base_dir}/knowledge

【支持格式】
PDF、Markdown、TXT

【搜索工具选择】
┌─────────────────────┬─────────────────────┬─────────────────────────┐
│      场景           │     推荐工具        │         原因            │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ 搜索知识库文档      │ search_knowledge   │ 搜索PDF/MD/TXT文档      │
│ 搜索项目源代码      │ search_codebase    │ 基于语义搜索代码        │
│ 知道函数/变量名     │ grep               │ 精确匹配代码            │
└─────────────────────┴─────────────────────┴─────────────────────────┘
""".format(base_dir=base_dir),
        func=sync_search_func,
        args_schema=SearchKnowledgeInput,
        coroutine=search_func
    )
