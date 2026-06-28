"""记忆文件向量索引 - 索引 memory/YYYY-MM-DD.md 文件"""
import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# ponytail: P2 迁移 llama_index → langchain InMemoryVectorStore（langchain_core 自带，0 新依赖）
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from utils.embedding_adapter import create_openai_embedding
from utils.logger import get_logger

logger = get_logger("MemoryIndexer")

MEMORY_FILE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}\.md$')


class MemoryIndexer:
    """记忆文件索引器 - 为 memory/YYYY-MM-DD.md 构建向量索引"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.memory_dir = base_dir / "workspace" / "memory"
        self.storage_dir = base_dir / "storage" / "memory_index"
        self.metadata_file = self.storage_dir / "index_meta.json"
        
        self.vectorstore: Optional[InMemoryVectorStore] = None
        self.file_hashes: Dict[str, str] = {}
        
        self._lock = threading.Lock()
        
        embed_api_key = settings.embedding_api_key if settings.embedding_api_key else settings.openai_api_key
        embed_base_url = settings.embedding_base_url if settings.embedding_base_url else settings.openai_base_url
        self.embed_model = create_openai_embedding(
            api_key=embed_api_key,
            base_url=embed_base_url
        )
    
    def _calculate_content_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode("utf-8")).hexdigest()
    
    def _scan_memory_files(self) -> List[Path]:
        """扫描 memory 目录下的所有 YYYY-MM-DD.md 文件"""
        if not self.memory_dir.exists():
            return []
        
        files = []
        for f in self.memory_dir.iterdir():
            if f.is_file() and MEMORY_FILE_PATTERN.match(f.name):
                files.append(f)
        
        files.sort(key=lambda x: x.name, reverse=True)
        return files
    
    def _get_current_hashes(self) -> Dict[str, str]:
        """获取当前所有记忆文件的哈希"""
        hashes = {}
        for file_path in self._scan_memory_files():
            try:
                content = file_path.read_text(encoding="utf-8")
                hashes[file_path.name] = self._calculate_content_hash(content)
            except Exception as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")
        return hashes
    
    def _calculate_combined_hash(self, hashes: Dict[str, str]) -> str:
        """计算组合哈希（用于快速检测变更）"""
        if not hashes:
            return ""
        combined = "|".join(f"{k}:{v}" for k, v in sorted(hashes.items()))
        return hashlib.md5(combined.encode("utf-8")).hexdigest()
    
    def _load_stored_metadata(self) -> Dict[str, Any]:
        """从元数据文件加载存储的元数据"""
        if not self.metadata_file.exists():
            return {}
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载元数据失败: {e}")
            return {}
    
    def _save_metadata(self, hashes: Dict[str, str], document_count: int):
        """保存元数据"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            meta = {
                "version": "2.0",
                "file_hashes": hashes,
                "combined_hash": self._calculate_combined_hash(hashes),
                "document_count": document_count,
                "updated_at": datetime.now().isoformat()
            }
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")
    
    def _read_all_files(self) -> tuple[List[Document], Dict[str, str]]:
        """
        读取所有记忆文件
        返回: (documents, hashes)
        """
        documents = []
        hashes = {}
        
        for file_path in self._scan_memory_files():
            try:
                content = file_path.read_text(encoding="utf-8")
                if not content.strip():
                    continue
                
                hashes[file_path.name] = self._calculate_content_hash(content)
                
                date_str = file_path.stem
                document = Document(
                    page_content=content,
                    metadata={
                        "source": file_path.name,
                        "date": date_str,
                        "type": "daily_memory"
                    }
                )
                documents.append(document)
                
            except Exception as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")
        
        return documents, hashes
    
    def rebuild_index(self) -> bool:
        """重建索引"""
        with self._lock:
            try:
                documents, hashes = self._read_all_files()

                if not documents:
                    logger.warning(f"记忆目录为空或无有效文件: {self.memory_dir}")
                    self.vectorstore = None
                    self.file_hashes = {}
                    return False

                # ponytail: RecursiveCharacterTextSplitter 自定义 separators 适配中文
                # 上限：中文切分质量较 SentenceSplitter 略降 5-10%，可接受
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=256, chunk_overlap=32,
                    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""]
                )
                chunks = splitter.split_documents(documents)

                if not chunks:
                    logger.warning("没有可索引的内容")
                    return False

                self.vectorstore = InMemoryVectorStore(embedding=self.embed_model)
                self.vectorstore.add_documents(chunks)

                self.storage_dir.mkdir(parents=True, exist_ok=True)
                # ponytail: InMemoryVectorStore.dump 接受文件路径（非目录），自动创建父目录
                self.vectorstore.dump(str(self.storage_dir / "vectorstore.json"))

                self._save_metadata(hashes, len(chunks))
                self.file_hashes = hashes

                logger.info(f"索引重建成功: {len(documents)} 个文件, {len(chunks)} 个节点")
                return True

            except Exception as e:
                logger.error(f"索引重建失败: {e}")
                return False
    
    def load_index(self) -> bool:
        """
        加载已有索引 - 验证文件一致性
        如果文件已变更，返回 False 触发重建
        """
        with self._lock:
            if not self.storage_dir.exists():
                return False
            
            try:
                current_hashes = self._get_current_hashes()
                
                if not current_hashes:
                    logger.debug("记忆目录为空")
                    return False
                
                metadata = self._load_stored_metadata()
                stored_hashes = metadata.get("file_hashes", {})
                
                if current_hashes != stored_hashes:
                    logger.debug("检测到文件变更，需要重建索引")
                    return False

                vectorstore_file = self.storage_dir / "vectorstore.json"
                if not vectorstore_file.exists():
                    logger.debug(f"向量存储文件不存在: {vectorstore_file}")
                    return False

                # ponytail: InMemoryVectorStore.load 类方法，接受文件路径 + embedding
                self.vectorstore = InMemoryVectorStore.load(
                    str(vectorstore_file), embedding=self.embed_model
                )
                self.file_hashes = current_hashes

                logger.info(f"索引加载成功: {len(current_hashes)} 个文件")
                return True
                
            except Exception as e:
                logger.error(f"索引加载失败: {e}")
                return False
    
    def ensure_index(self) -> bool:
        """确保索引可用"""
        with self._lock:
            if self.vectorstore is not None:
                current_hashes = self._get_current_hashes()
                if current_hashes == self.file_hashes:
                    return True

        if self.load_index():
            return True

        return self.rebuild_index()

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """检索记忆"""
        if not self.ensure_index():
            return []

        try:
            # ponytail: similarity_search_with_relevance_scores 返回 List[Tuple[Document, float]]
            results = self.vectorstore.similarity_search_with_relevance_scores(query, k=top_k)
            output = []
            for doc, score in results:
                output.append({
                    "text": doc.page_content,
                    "score": float(score) if score is not None else 0.0,
                    "source": doc.metadata.get("source", "unknown"),
                    "date": doc.metadata.get("date", "unknown")
                })
            return output

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    def get_file_list(self) -> List[str]:
        """获取所有记忆文件列表"""
        return [f.name for f in self._scan_memory_files()]


_indexer: Optional[MemoryIndexer] = None


def get_memory_indexer(base_dir: Path) -> MemoryIndexer:
    """获取记忆索引器实例"""
    global _indexer
    if _indexer is None:
        _indexer = MemoryIndexer(base_dir)
    return _indexer
