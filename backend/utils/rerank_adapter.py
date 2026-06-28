"""Rerank 适配器 - 对检索结果重排序"""
from typing import List, Dict, Any
import httpx

from config import settings, get_config_manager
from utils.logger import get_logger

logger = get_logger("RerankAdapter")


def _get_rerank_config() -> Dict[str, Any]:
    """
    获取 Rerank 配置
    优先从 config_manager 读取当前模型配置，如果没有则回退到 .env 默认值
    """
    config_manager = get_config_manager()
    if config_manager:
        current_model = config_manager.get_current_model("rerank")
        if current_model:
            logger.debug(f"使用 ConfigManager 中的 Rerank 配置: {current_model['name']}")
            return current_model
    
    # 回退到 .env 默认值
    logger.debug("使用 .env 中的 Rerank 默认配置")
    return {
        "model": settings.rerank_model,
        "api_key": settings.rerank_api_key if settings.rerank_api_key else settings.openai_api_key,
        "base_url": settings.rerank_base_url if settings.rerank_base_url else settings.openai_base_url,
    }


class OpenAIReranker:
    """OpenAI 兼容 Rerank 适配器"""

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        model_id: str = None
    ):
        """
        初始化 Reranker

        Args:
            model: 模型名称，默认从配置读取
            api_key: API Key，默认从配置读取
            base_url: API Base URL，默认从配置读取
            model_id: 指定要使用的模型 ID，如果不指定则使用当前模型
        """
        try:
            # 获取模型配置
            cm = get_config_manager()
            if model_id and cm:
                # 使用指定的模型 ID
                model_config = cm.get_model("rerank", model_id)
                if not model_config:
                    logger.warning(f"指定的模型 ID {model_id} 不存在，使用当前模型")
                    model_config = _get_rerank_config()
                else:
                    # 获取完整配置（包含未脱敏的 API Key）
                    for m in cm._get_model_config("rerank"):
                        if m["id"] == model_id:
                            model_config = m.copy()
                            break
            else:
                model_config = _get_rerank_config()

            # 使用传入的参数覆盖配置
            self.model = model if model is not None else model_config["model"]
            self.api_key = api_key if api_key is not None else model_config["api_key"]
            base_url = base_url if base_url is not None else model_config["base_url"]
            
            # 尝试使用 OpenAI 兼容的 rerank 端点
            self.base_url = base_url.rstrip('/')
            # 常见的 rerank 端点路径
            self.rerank_endpoints = [
                "/rerank",
                "/v1/rerank",
                "/api/v1/rerank",
            ]

            if not self.api_key:
                logger.warning("Reranker API Key 未设置，将使用降级方案")
            else:
                logger.debug(f"Reranker 初始化成功: model={self.model}, base_url={self.base_url}")
        except Exception as e:
            logger.error(f"Reranker 初始化失败: {type(e).__name__}: {e}")
            raise

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        return_documents: bool = True
    ) -> List[Dict[str, Any]]:
        """
        对文档进行重排序

        Args:
            query: 查询文本
            documents: 待排序的文档列表，每项包含 text 和其他元数据
            top_k: 返回前 K 个结果
            return_documents: 是否返回文档内容

        Returns:
            重排序后的文档列表，包含 relevance_score
        """
        if not documents:
            logger.debug("文档列表为空，跳过 Rerank")
            return []

        if not self.api_key:
            logger.warning("API Key 未设置，跳过 Rerank，返回原始顺序")
            return documents[:top_k]

        # 尝试各个 rerank 端点
        texts = [doc.get("text", "") for doc in documents]

        for endpoint in self.rerank_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"

                payload = {
                    "model": self.model,
                    "query": query,
                    "documents": texts,
                    "top_n": min(top_k, len(documents)),
                }

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                logger.debug(f"尝试 Rerank 端点: {endpoint}, query长度={len(query)}, 文档数={len(documents)}, top_k={top_k}")

                # ponytail: httpx 替代 requests，openai SDK 已传递依赖 httpx
                response = httpx.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()

                    # 处理不同格式的响应
                    if "results" in result:
                        # Cohere/OpenAI 格式
                        return self._parse_results(result["results"], documents, top_k)
                    elif "data" in result:
                        # 另一种常见格式
                        return self._parse_results(result["data"], documents, top_k)
                    elif "output" in result and "results" in result["output"]:
                        # DashScope 格式
                        return self._parse_dashscope_results(result["output"]["results"], documents, top_k)

            except httpx.TimeoutException:
                logger.debug(f"Rerank 端点 {endpoint} 超时")
                continue
            except httpx.ConnectError:
                logger.debug(f"Rerank 端点 {endpoint} 连接失败")
                continue
            except Exception as e:
                logger.debug(f"Rerank 端点 {endpoint} 失败: {e}")
                continue

        # 所有端点都失败，返回原始顺序
        logger.warning("所有 Rerank 端点都失败，返回原始顺序")
        return documents[:top_k]

    def _parse_results(self, results: List[Dict], documents: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """解析标准格式的 rerank 结果"""
        reranked_results = []
        for item in results[:top_k]:
            idx = item.get("index", 0)
            score = item.get("relevance_score") or item.get("score", 0.0)

            if 0 <= idx < len(documents):
                doc = documents[idx].copy()
                doc["rerank_score"] = score
                doc["original_index"] = idx
                reranked_results.append(doc)

        logger.info(f"Rerank 成功: 返回 {len(reranked_results)} 个结果")
        return reranked_results

    def _parse_dashscope_results(self, results: List[Dict], documents: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """解析 DashScope 格式的 rerank 结果"""
        reranked_results = []
        for item in results[:top_k]:
            idx = item.get("index", 0)
            score = item.get("relevance_score", 0.0)

            if 0 <= idx < len(documents):
                doc = documents[idx].copy()
                doc["rerank_score"] = score
                doc["original_index"] = idx
                if "document" in item and "text" in item["document"]:
                    doc["text"] = item["document"]["text"]
                reranked_results.append(doc)

        logger.info(f"Rerank 成功: 返回 {len(reranked_results)} 个结果")
        return reranked_results

    def rerank_with_texts(
        self,
        query: str,
        texts: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        简化版：直接传入文本列表进行重排序

        Args:
            query: 查询文本
            texts: 文本列表
            top_k: 返回前 K 个结果

        Returns:
            重排序后的结果列表，包含 index, text, rerank_score
        """
        if not texts:
            logger.debug("文本列表为空，跳过 Rerank")
            return []

        documents = [{"text": text} for text in texts]
        logger.debug(f"rerank_with_texts: 转换 {len(texts)} 个文本为文档格式")
        results = self.rerank(query, documents, top_k)
        return results


class FallbackReranker:
    """降级 Reranker - 当 API 不可用时使用简单的基于 embedding 相似度的重排序"""

    def __init__(self, embed_model=None):
        self.embed_model = embed_model
        if not self.embed_model:
            logger.warning("FallbackReranker 初始化: 未提供 embedding 模型")
        else:
            logger.debug("FallbackReranker 初始化成功")

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        return_documents: bool = True
    ) -> List[Dict[str, Any]]:
        """使用 embedding 余弦相似度进行重排序"""
        if not self.embed_model or not documents:
            logger.debug(f"FallbackReranker: 跳过处理 (embed_model={bool(self.embed_model)}, documents={len(documents) if documents else 0})")
            return documents[:top_k] if documents else []

        try:
            import numpy as np

            logger.debug(f"FallbackReranker 开始本地重排序: query长度={len(query)}, 文档数={len(documents)}")

            # 获取 query embedding
            # ponytail: P2 迁移后 embed_model 是 langchain OpenAIEmbeddings，API 改名
            query_embedding = self.embed_model.embed_query(query)
            query_vec = np.array(query_embedding)

            # 计算每个文档的相似度
            scored_docs = []
            for i, doc in enumerate(documents):
                text = doc.get("text", "")
                if not text:
                    scored_docs.append((i, 0.0, doc))
                    continue

                try:
                    # ponytail: P2 迁移后用 embed_documents（批量 API，取首个）
                    doc_embedding = self.embed_model.embed_documents([text])[0]
                    doc_vec = np.array(doc_embedding)

                    # 余弦相似度（添加除零保护）
                    query_norm = np.linalg.norm(query_vec)
                    doc_norm = np.linalg.norm(doc_vec)

                    if query_norm == 0 or doc_norm == 0:
                        logger.debug(f"FallbackReranker: 文档 {i} 的向量范数为零，跳过计算")
                        scored_docs.append((i, 0.0, doc))
                        continue

                    similarity = np.dot(query_vec, doc_vec) / (query_norm * doc_norm)
                    scored_docs.append((i, float(similarity), doc))
                except Exception as e:
                    logger.debug(f"FallbackReranker: 文档 {i} embedding 计算失败: {e}")
                    scored_docs.append((i, 0.0, doc))

            # 按分数排序
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            # 返回前 top_k 个
            results = []
            for idx, score, doc in scored_docs[:top_k]:
                doc_copy = doc.copy()
                doc_copy["rerank_score"] = score
                doc_copy["original_index"] = idx
                results.append(doc_copy)

            logger.info(f"FallbackReranker 重排序完成: 返回 {len(results)} 个结果")
            return results

        except ImportError:
            logger.error("FallbackReranker 失败: 未安装 numpy")
            return documents[:top_k] if documents else []
        except Exception as e:
            logger.error(f"FallbackReranker 重排序失败: {type(e).__name__}: {e}")
            return documents[:top_k] if documents else []


# 保持向后兼容的类名
DashScopeReranker = OpenAIReranker


def create_reranker(
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    embed_model=None,
    model_id: str = None
):
    """
    创建 Reranker 实例

    Args:
        model: 模型名称
        api_key: API Key
        base_url: API Base URL
        embed_model: 可选，用于降级方案的 embedding 模型
        model_id: 指定要使用的模型 ID，如果不指定则使用当前模型

    Returns:
        OpenAIReranker 或 FallbackReranker 实例
    """
    try:
        # 首先尝试创建 OpenAIReranker
        reranker = OpenAIReranker(
            model=model,
            api_key=api_key,
            base_url=base_url,
            model_id=model_id
        )
        # 检查 API Key 是否有效，如果无效则使用降级方案
        if not reranker.api_key:
            logger.warning("API Key 未设置，使用 FallbackReranker")
            if embed_model:
                return FallbackReranker(embed_model=embed_model)
            else:
                logger.warning("未提供 embed_model，FallbackReranker 将不可用")
        logger.info(f"Reranker 创建成功: model={model or 'default'}")
        return reranker
    except Exception as e:
        logger.error(f"OpenAIReranker 创建失败: {type(e).__name__}: {e}")
        # 创建失败时使用 FallbackReranker 作为降级
        if embed_model:
            logger.info("使用 FallbackReranker 作为降级方案")
            return FallbackReranker(embed_model=embed_model)
        raise


def get_available_rerank_models():
    """
    获取所有可用的 Rerank 模型列表
    
    Returns:
        模型列表，包含 id, name, model, is_default 等信息
    """
    cm = get_config_manager()
    if cm:
        return cm.get_models("rerank")
    return []


def get_current_rerank_model():
    """
    获取当前使用的 Rerank 模型配置
    
    Returns:
        当前模型配置
    """
    return _get_rerank_config()
