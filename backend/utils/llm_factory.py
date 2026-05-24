"""LLM 工厂函数 - 统一管理 LLM 实例创建"""
from langchain_openai import ChatOpenAI

from config import settings, get_config_manager
from utils.logger import get_logger

logger = get_logger("LLMFactory")


def _get_llm_config():
    """
    获取 LLM 配置
    优先从 config_manager 读取当前模型配置，如果没有则回退到 .env 默认值
    """
    config_manager = get_config_manager()
    if config_manager:
        current_model = config_manager.get_current_model("llm")
        if current_model:
            logger.debug(f"使用 ConfigManager 中的 LLM 配置: {current_model['name']}")
            return current_model
    
    # 回退到 .env 默认值
    logger.debug("使用 .env 中的 LLM 默认配置")
    return {
        "model": settings.llm_model,
        "api_key": settings.openai_api_key,
        "base_url": settings.openai_base_url,
    }


def create_llm(
    temperature: float = None,
    streaming: bool = False,
    override_params: dict = None,
    model_id: str = None
) -> ChatOpenAI:
    """
    创建 OpenAI LLM 实例

    优先使用传入的参数，未传入的从配置管理器读取默认值

    Args:
        temperature: 温度参数，控制随机性 (默认从配置读取)
        streaming: 是否启用流式输出
        override_params: 额外覆盖的参数字典
        model_id: 指定要使用的模型 ID，如果不指定则使用当前模型

    Returns:
        ChatOpenAI 实例
    """
    config_manager = get_config_manager()
    
    try:
        # 从配置管理器获取参数
        if config_manager:
            params = config_manager.llm_params
        else:
            params = {}
            logger.debug("config_manager 未初始化，使用默认参数创建 LLM")

        # 获取模型配置
        if model_id and config_manager:
            # 使用指定的模型 ID
            model_config = config_manager.get_model("llm", model_id)
            if not model_config:
                logger.warning(f"指定的模型 ID {model_id} 不存在，使用当前模型")
                model_config = _get_llm_config()
            else:
                # 获取完整配置（包含未脱敏的 API Key）
                for m in config_manager._get_model_config("llm"):
                    if m["id"] == model_id:
                        model_config = m.copy()
                        break
        else:
            model_config = _get_llm_config()

        # 基础参数（使用传入值 > 配置值 > 默认值）
        final_temperature = temperature if temperature is not None else params.get("temperature", 0.7)

        llm_kwargs = {
            "model": model_config["model"],
            "api_key": model_config["api_key"],
            "base_url": model_config["base_url"],
            "temperature": final_temperature,
            "top_p": params.get("top_p", 0.8),
            "presence_penalty": params.get("presence_penalty", 0.0),
            "max_tokens": params.get("max_tokens", 40960),
            "streaming": streaming,
        }

        logger.debug(f"创建LLM实例: model={model_config['model']}, temperature={final_temperature}, streaming={streaming}")

        # 应用额外覆盖参数
        if override_params:
            # 过滤掉 LangChain ChatOpenAI 不支持的参数
            filtered_params = override_params.copy()
            unsupported_params = ["thinking_enabled"]
            for param in unsupported_params:
                if param in filtered_params:
                    del filtered_params[param]
                    logger.debug(f"过滤掉不支持的参数: {param}")
            llm_kwargs.update(filtered_params)
            logger.debug(f"应用覆盖参数: {filtered_params}")

        llm = ChatOpenAI(**llm_kwargs)
        logger.info(f"LLM实例创建成功: model={model_config['model']}")
        return llm

    except ImportError as e:
        logger.error(f"LLM库导入失败: {e}")
        raise
    except Exception as e:
        logger.error(f"LLM实例创建失败: {type(e).__name__}: {e}")
        raise


def get_available_llm_models():
    """
    获取所有可用的 LLM 模型列表
    
    Returns:
        模型列表，包含 id, name, model, is_default 等信息
    """
    cm = get_config_manager()
    if cm:
        return cm.get_models("llm")
    return []


def get_current_llm_model():
    """
    获取当前使用的 LLM 模型配置
    
    Returns:
        当前模型配置
    """
    return _get_llm_config()
