"""Embedding 适配器 - 使用 OpenAI 兼容接口"""
from typing import List, Optional, Dict, Any

from llama_index.core.embeddings import BaseEmbedding
from langchain_openai import OpenAIEmbeddings

from config import settings, get_config_manager
from utils.logger import get_logger

logger = get_logger("EmbeddingAdapter")


class LangChainEmbedding(BaseEmbedding):
    """LlamaIndex 的 LangChain Embedding 适配器"""

    def __init__(self, langchain_embeddings=None, **kwargs):
        # 添加父类初始化的错误处理
        try:
            super().__init__(**kwargs)
        except Exception as e:
            logger.error(f"Embedding 适配器父类初始化失败: {type(e).__name__}: {e}")
            raise
        self._langchain_embeddings = langchain_embeddings

    def _get_query_embedding(self, query: str) -> List[float]:
        """获取查询文本的 embedding"""
        try:
            embeddings = self._langchain_embeddings.embed_query(query)
            logger.debug(f"查询文本 embedding 获取成功，维度={len(embeddings)}")
            return embeddings
        except Exception as e:
            logger.error(f"查询文本 embedding 获取失败: {type(e).__name__}: {e}")
            raise

    def _get_text_embedding(self, text: str) -> List[float]:
        """获取单个文本的 embedding"""
        try:
            embeddings = self._langchain_embeddings.embed_documents([text])
            logger.debug(f"单文本 embedding 获取成功，维度={len(embeddings[0])}")
            return embeddings[0]
        except Exception as e:
            logger.error(f"单文本 embedding 获取失败: {type(e).__name__}: {e}")
            raise

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本的 embeddings"""
        try:
            embeddings = self._langchain_embeddings.embed_documents(texts)
            logger.debug(f"批量 embedding 获取成功，数量={len(embeddings)}, 维度={len(embeddings[0]) if embeddings else 0}")
            return embeddings
        except Exception as e:
            logger.error(f"批量 embedding 获取失败: {type(e).__name__}: {e}")
            raise

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """异步获取查询文本的 embedding"""
        try:
            return self._get_query_embedding(query)
        except Exception as e:
            logger.error(f"异步查询 embedding 获取失败: {type(e).__name__}: {e}")
            raise

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """异步获取单个文本的 embedding"""
        try:
            return self._get_text_embedding(text)
        except Exception as e:
            logger.error(f"异步单文本 embedding 获取失败: {type(e).__name__}: {e}")
            raise

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """异步批量获取文本的 embeddings"""
        try:
            return self._get_text_embeddings(texts)
        except Exception as e:
            logger.error(f"异步批量 embedding 获取失败: {type(e).__name__}: {e}")
            raise


def _get_embedding_config() -> Dict[str, Any]:
    """
    获取 Embedding 配置
    优先从 config_manager 读取当前模型配置，如果没有则回退到 .env 默认值
    """
    config_manager = get_config_manager()
    if config_manager:
        current_model = config_manager.get_current_model("embedding")
        if current_model:
            logger.debug(f"使用 ConfigManager 中的 Embedding 配置: {current_model['name']}")
            return current_model
    
    # 回退到 .env 默认值
    logger.debug("使用 .env 中的 Embedding 默认配置")
    return {
        "model": settings.embedding_model,
        "api_key": settings.embedding_api_key if settings.embedding_api_key else settings.openai_api_key,
        "base_url": settings.embedding_base_url if settings.embedding_base_url else settings.openai_base_url,
    }


def create_openai_embedding(
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    model_id: str = None
):
    """
    创建 OpenAI Embedding 实例

    Args:
        model: 模型名称，默认从配置读取
        api_key: OpenAI API Key，默认从配置读取
        base_url: OpenAI Base URL，默认从配置读取
        model_id: 指定要使用的模型 ID，如果不指定则使用当前模型

    Returns:
        LangChainEmbedding 实例

    Raises:
        RuntimeError: 如果创建失败
    """
    try:
        # 获取模型配置
        cm = get_config_manager()
        if model_id and cm:
            # 使用指定的模型 ID
            model_config = cm.get_model("embedding", model_id)
            if not model_config:
                logger.warning(f"指定的模型 ID {model_id} 不存在，使用当前模型")
                model_config = _get_embedding_config()
            else:
                # 获取完整配置（包含未脱敏的 API Key）
                for m in cm._get_model_config("embedding"):
                    if m["id"] == model_id:
                        model_config = m.copy()
                        break
        else:
            model_config = _get_embedding_config()

        # 使用传入的参数覆盖配置
        final_model = model if model is not None else model_config["model"]
        final_api_key = api_key if api_key is not None else model_config["api_key"]
        final_base_url = base_url if base_url is not None else model_config["base_url"]

        lc_embeddings = OpenAIEmbeddings(
            model=final_model,
            api_key=final_api_key,
            base_url=final_base_url
        )
        logger.info(f"OpenAI Embedding 创建成功: model={final_model}, base_url={final_base_url}")
        return LangChainEmbedding(langchain_embeddings=lc_embeddings)
    except Exception as e:
        logger.error(f"OpenAI Embedding 创建失败: {type(e).__name__}: {e}")
        raise


def get_available_embedding_models():
    """
    获取所有可用的 Embedding 模型列表
    
    Returns:
        模型列表，包含 id, name, model, is_default 等信息
    """
    cm = get_config_manager()
    if cm:
        return cm.get_models("embedding")
    return []


def get_current_embedding_model():
    """
    获取当前使用的 Embedding 模型配置
    
    Returns:
        当前模型配置
    """
    return _get_embedding_config()


# 保持向后兼容的别名
create_dashscope_embedding = create_openai_embedding
