"""Embedding 适配器 - 使用 OpenAI 兼容接口

ponytail: P2 迁移删 llama_index BaseEmbedding 包装，直接返回 langchain OpenAIEmbeddings。
llama_index → InMemoryVectorStore 迁移后，所有调用方使用 langchain 原生 embed_query/embed_documents API。
"""
from typing import List, Dict, Any

from langchain_openai import OpenAIEmbeddings

from config import settings, get_config_manager
from utils.logger import get_logger

logger = get_logger("EmbeddingAdapter")


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
) -> OpenAIEmbeddings:
    """
    创建 OpenAI Embedding 实例

    Args:
        model: 模型名称，默认从配置读取
        api_key: OpenAI API Key，默认从配置读取
        base_url: OpenAI Base URL，默认从配置读取
        model_id: 指定要使用的模型 ID，如果不指定则使用当前模型

    Returns:
        OpenAIEmbeddings 实例（langchain_openai 原生）

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

        embeddings = OpenAIEmbeddings(
            model=final_model,
            api_key=final_api_key,
            base_url=final_base_url
        )
        logger.info(f"OpenAI Embedding 创建成功: model={final_model}, base_url={final_base_url}")
        return embeddings
    except Exception as e:
        logger.error(f"OpenAI Embedding 创建失败: {type(e).__name__}: {e}")
        raise


def get_available_embedding_models() -> List[Dict[str, Any]]:
    """获取所有可用的 Embedding 模型列表"""
    cm = get_config_manager()
    if cm:
        return cm.get_models("embedding")
    return []


def get_current_embedding_model() -> Dict[str, Any]:
    """获取当前使用的 Embedding 模型配置"""
    return _get_embedding_config()


# 保持向后兼容的别名
create_dashscope_embedding = create_openai_embedding
