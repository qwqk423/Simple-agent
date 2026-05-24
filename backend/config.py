"""全局配置管理"""
import os
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, BaseModel
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from utils.logger import get_logger

logger = get_logger("Config")


class Settings(BaseSettings):
    """环境变量配置 - 作为默认值使用"""
    # LLM API 配置 (OpenAI 兼容)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    
    # Embedding API 配置 (独立配置，默认使用 OPENAI 配置)
    embedding_api_key: str = Field(default="", alias="EMBEDDING_API_KEY")
    embedding_base_url: str = Field(default="", alias="EMBEDDING_BASE_URL")
    
    # Rerank API 配置 (独立配置，默认使用 OPENAI 配置)
    rerank_api_key: str = Field(default="", alias="RERANK_API_KEY")
    rerank_base_url: str = Field(default="", alias="RERANK_BASE_URL")
    
    # LLM 模型配置
    llm_model: str = Field(default="qwen3.5-27b", alias="LLM_MODEL")
    
    # Embedding 模型配置
    embedding_model: str = Field(default="text-embedding-v4", alias="EMBEDDING_MODEL")
    
    # Rerank 模型配置
    rerank_model: str = Field(default="qwen3-vl-rerank", alias="RERANK_MODEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


class ModelConfig(BaseModel):
    """单个模型配置"""
    id: str
    name: str
    model: str
    api_key: str
    base_url: str
    is_default: bool = False


class ModelConfigs(BaseModel):
    """模型配置列表"""
    models: List[ModelConfig]
    current_model_id: Optional[str] = None


class ConfigManager:
    """配置管理器 - 持久化配置到 JSON 文件"""
    
    # LLM 默认参数
    DEFAULT_LLM_PARAMS = {
        "temperature": 0.7,
        "top_p": 0.8,
        "presence_penalty": 0.0,
        "max_tokens": 8192,
        "thinking_enabled": True,
    }
    
    def __init__(self, base_dir: Path):
        self.config_path = base_dir / "config.json"
        try:
            self._config = self._load()
            # 初始化模型配置
            self._init_model_configs()
        except Exception as e:
            logger.error(f"配置加载失败，使用默认配置: {e}")
            self._config = {"rag_mode": False, **self.DEFAULT_LLM_PARAMS}
            self._init_model_configs()
    
    def _load(self) -> dict:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    logger.debug(f"配置文件加载成功: {self.config_path}")
                    # 合并默认参数
                    merged_count = 0
                    for key, value in self.DEFAULT_LLM_PARAMS.items():
                        if key not in loaded:
                            loaded[key] = value
                            merged_count += 1
                    if merged_count > 0:
                        logger.debug(f"合并默认参数: {merged_count} 个")
                    return loaded
            except json.JSONDecodeError as e:
                logger.error(f"配置文件格式错误 [{self.config_path}]: {e}")
            except UnicodeDecodeError as e:
                logger.error(f"配置文件编码错误 [{self.config_path}]: {e}")
            except PermissionError as e:
                logger.error(f"配置文件读取权限不足 [{self.config_path}]: {e}")
            except Exception as e:
                logger.error(f"配置文件加载失败 [{self.config_path}]: {type(e).__name__}: {e}")
            logger.warning("将使用默认配置")
        else:
            logger.debug(f"配置文件不存在，使用默认配置: {self.config_path}")
        return {"rag_mode": False, **self.DEFAULT_LLM_PARAMS}
    
    def _init_model_configs(self):
        """初始化模型配置，如果没有则从 .env 创建默认值"""
        # LLM 模型配置
        if "llm_models" not in self._config:
            self._config["llm_models"] = []
        if not self._config["llm_models"]:
            # 从 .env 创建默认 LLM 配置
            default_llm = {
                "id": str(uuid.uuid4()),
                "name": "默认模型",
                "model": settings.llm_model,
                "api_key": settings.openai_api_key,
                "base_url": settings.openai_base_url,
                "is_default": True
            }
            self._config["llm_models"] = [default_llm]
            self._config["current_llm_model_id"] = default_llm["id"]
            logger.info("从 .env 初始化默认 LLM 配置")
        
        # Embedding 模型配置
        if "embedding_models" not in self._config:
            self._config["embedding_models"] = []
        if not self._config["embedding_models"]:
            # 从 .env 创建默认 Embedding 配置
            default_embedding = {
                "id": str(uuid.uuid4()),
                "name": "默认Embedding模型",
                "model": settings.embedding_model,
                "api_key": settings.embedding_api_key if settings.embedding_api_key else settings.openai_api_key,
                "base_url": settings.embedding_base_url if settings.embedding_base_url else settings.openai_base_url,
                "is_default": True
            }
            self._config["embedding_models"] = [default_embedding]
            self._config["current_embedding_model_id"] = default_embedding["id"]
            logger.info("从 .env 初始化默认 Embedding 配置")
        
        # Rerank 模型配置
        if "rerank_models" not in self._config:
            self._config["rerank_models"] = []
        if not self._config["rerank_models"]:
            # 从 .env 创建默认 Rerank 配置
            default_rerank = {
                "id": str(uuid.uuid4()),
                "name": "默认Rerank模型",
                "model": settings.rerank_model,
                "api_key": settings.rerank_api_key if settings.rerank_api_key else settings.openai_api_key,
                "base_url": settings.rerank_base_url if settings.rerank_base_url else settings.openai_base_url,
                "is_default": True
            }
            self._config["rerank_models"] = [default_rerank]
            self._config["current_rerank_model_id"] = default_rerank["id"]
            logger.info("从 .env 初始化默认 Rerank 配置")
        
        self.save()
    
    def save(self):
        """保存配置（原子写入，防止写入中断导致配置文件损坏）"""
        import os
        import tempfile
        
        try:
            # 使用临时文件+重命名的方式实现原子写入
            config_dir = self.config_path.parent
            # 在配置目录下创建临时文件，确保在同一文件系统内
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                suffix='.tmp',
                prefix='config_',
                dir=config_dir,
                delete=False
            ) as f:
                temp_path = Path(f.name)
                json.dump(self._config, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # 确保数据写入磁盘
            
            # 原子替换目标文件
            temp_path.replace(self.config_path)
            logger.debug(f"配置保存成功: {self.config_path}")
        except PermissionError as e:
            logger.error(f"配置保存失败，权限不足 [{self.config_path}]: {e}")
            # 清理临时文件
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise
        except Exception as e:
            logger.error(f"配置保存失败 [{self.config_path}]: {type(e).__name__}: {e}")
            # 清理临时文件
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        """设置配置项"""
        self._config[key] = value
        self.save()
    
    @property
    def rag_mode(self) -> bool:
        """RAG 模式开关"""
        return self._config.get("rag_mode", False)
    
    @rag_mode.setter
    def rag_mode(self, value: bool):
        self._config["rag_mode"] = value
        self.save()
    
    # LLM 参数属性
    @property
    def llm_params(self) -> dict:
        """获取所有 LLM 参数"""
        return {
            "temperature": self._config.get("temperature", self.DEFAULT_LLM_PARAMS["temperature"]),
            "top_p": self._config.get("top_p", self.DEFAULT_LLM_PARAMS["top_p"]),
            "presence_penalty": self._config.get("presence_penalty", self.DEFAULT_LLM_PARAMS["presence_penalty"]),
            "max_tokens": self._config.get("max_tokens", self.DEFAULT_LLM_PARAMS["max_tokens"]),
            "thinking_enabled": self._config.get("thinking_enabled", self.DEFAULT_LLM_PARAMS["thinking_enabled"]),
        }
    
    def update_llm_param(self, key: str, value):
        """更新单个 LLM 参数"""
        logger.debug(f"更新LLM参数: key={key}, value={value}, type={type(value).__name__}")
        if key in self.DEFAULT_LLM_PARAMS:
            old_value = self._config.get(key)
            self._config[key] = value
            try:
                self.save()
                logger.info(f"LLM参数更新成功: {key} = {value} (原值: {old_value})")
            except Exception as e:
                # 保存失败时回滚
                self._config[key] = old_value
                logger.error(f"LLM参数更新失败，已回滚: {key} = {old_value}")
                raise
        else:
            logger.warning(f"未知的LLM参数: {key}")
            raise ValueError(f"未知的 LLM 参数: {key}")
    
    # ==================== 模型配置管理 ====================
    
    def _get_model_config(self, model_type: str) -> Dict[str, Any]:
        """获取指定类型的模型配置"""
        key = f"{model_type}_models"
        return self._config.get(key, [])
    
    def _set_model_config(self, model_type: str, models: List[Dict]):
        """设置指定类型的模型配置"""
        key = f"{model_type}_models"
        self._config[key] = models
        self.save()
    
    def _get_current_model_id(self, model_type: str) -> Optional[str]:
        """获取当前使用的模型 ID"""
        key = f"current_{model_type}_model_id"
        return self._config.get(key)
    
    def _set_current_model_id(self, model_type: str, model_id: str):
        """设置当前使用的模型 ID"""
        key = f"current_{model_type}_model_id"
        self._config[key] = model_id
        self.save()
    
    def get_models(self, model_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的所有模型配置"""
        models = self._get_model_config(model_type)
        # 返回时脱敏 API Key
        return [self._mask_api_key(model) for model in models]
    
    def get_model(self, model_type: str, model_id: str) -> Optional[Dict[str, Any]]:
        """获取指定模型配置"""
        models = self._get_model_config(model_type)
        for model in models:
            if model["id"] == model_id:
                return self._mask_api_key(model.copy())
        return None
    
    def add_model(self, model_type: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """添加新模型配置"""
        models = self._get_model_config(model_type)
        
        # 生成唯一 ID
        if "id" not in model_config or not model_config["id"]:
            model_config["id"] = str(uuid.uuid4())
        
        # 如果设置为默认，取消其他模型的默认状态
        if model_config.get("is_default"):
            for m in models:
                m["is_default"] = False
        
        # 如果是第一个模型，设为默认
        if not models:
            model_config["is_default"] = True
        
        models.append(model_config)
        self._set_model_config(model_type, models)
        
        # 如果没有设置当前模型，设为当前模型
        if not self._get_current_model_id(model_type):
            self._set_current_model_id(model_type, model_config["id"])
        
        logger.info(f"添加 {model_type} 模型: {model_config['name']} ({model_config['id']})")
        return self._mask_api_key(model_config.copy())
    
    def update_model(self, model_type: str, model_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新模型配置"""
        models = self._get_model_config(model_type)
        
        for i, model in enumerate(models):
            if model["id"] == model_id:
                # 如果设置为默认，取消其他模型的默认状态
                if updates.get("is_default") and not model.get("is_default"):
                    for m in models:
                        m["is_default"] = False
                
                # 更新字段
                for key, value in updates.items():
                    if key != "id":  # 不允许修改 ID
                        model[key] = value
                
                models[i] = model
                self._set_model_config(model_type, models)
                logger.info(f"更新 {model_type} 模型: {model['name']} ({model_id})")
                return self._mask_api_key(model.copy())
        
        return None
    
    def delete_model(self, model_type: str, model_id: str) -> bool:
        """删除模型配置"""
        models = self._get_model_config(model_type)
        
        # 不能删除唯一的模型
        if len(models) <= 1:
            logger.warning(f"不能删除唯一的 {model_type} 模型")
            return False
        
        for i, model in enumerate(models):
            if model["id"] == model_id:
                deleted_model = models.pop(i)
                
                # 如果删除的是默认模型，将第一个设为默认
                if deleted_model.get("is_default") and models:
                    models[0]["is_default"] = True
                
                self._set_model_config(model_type, models)
                
                # 如果删除的是当前使用的模型，切换到默认模型
                current_id = self._get_current_model_id(model_type)
                if current_id == model_id:
                    default_model = next((m for m in models if m.get("is_default")), models[0])
                    self._set_current_model_id(model_type, default_model["id"])
                
                logger.info(f"删除 {model_type} 模型: {deleted_model['name']} ({model_id})")
                return True
        
        return False
    
    def set_default_model(self, model_type: str, model_id: str) -> bool:
        """设置默认模型"""
        models = self._get_model_config(model_type)
        
        found = False
        for model in models:
            if model["id"] == model_id:
                model["is_default"] = True
                found = True
            else:
                model["is_default"] = False
        
        if found:
            self._set_model_config(model_type, models)
            logger.info(f"设置默认 {model_type} 模型: {model_id}")
        
        return found
    
    def get_current_model(self, model_type: str) -> Optional[Dict[str, Any]]:
        """获取当前使用的模型配置（包含完整的 API Key）"""
        current_id = self._get_current_model_id(model_type)
        models = self._get_model_config(model_type)
        
        logger.debug(f"get_current_model: type={model_type}, current_id={current_id}, models_count={len(models)}")
        
        # 先尝试找当前设置的模型
        if current_id:
            for model in models:
                if model["id"] == current_id:
                    logger.debug(f"找到当前模型: {model['name']} ({current_id})")
                    return model.copy()
            logger.warning(f"未找到 current_id={current_id} 对应的模型")
        
        # 如果没有当前模型，找默认模型
        for model in models:
            if model.get("is_default"):
                logger.debug(f"使用默认模型: {model['name']}")
                return model.copy()
        
        # 如果都没有，返回第一个
        if models:
            logger.debug(f"使用第一个模型: {models[0]['name']}")
            return models[0].copy()
        
        logger.warning(f"没有可用的 {model_type} 模型配置")
        return None
    
    def set_current_model(self, model_type: str, model_id: str) -> bool:
        """设置当前使用的模型"""
        models = self._get_model_config(model_type)
        
        for model in models:
            if model["id"] == model_id:
                self._set_current_model_id(model_type, model_id)
                logger.info(f"切换 {model_type} 模型: {model['name']} ({model_id})")
                # 验证是否正确设置
                saved_id = self._get_current_model_id(model_type)
                logger.debug(f"验证切换结果: saved_id={saved_id}, expected={model_id}")
                return True
        
        return False
    
    def _mask_api_key(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏 API Key"""
        masked = model.copy()
        if "api_key" in masked and masked["api_key"]:
            key = masked["api_key"]
            if len(key) > 8:
                masked["api_key"] = f"{key[:4]}...{key[-4:]}"
            else:
                masked["api_key"] = "****"
        return masked


# 全局配置管理器实例
config_manager: Optional[ConfigManager] = None
_base_dir: Optional[Path] = None  # 保存 base_dir 用于热重载时重新初始化


def init_config_manager(base_dir: Path):
    """初始化配置管理器"""
    global config_manager, _base_dir
    _base_dir = base_dir
    try:
        config_manager = ConfigManager(base_dir)
        logger.info(f"配置管理器初始化成功: {base_dir}")
        return config_manager
    except Exception as e:
        logger.error(f"配置管理器初始化失败 [{base_dir}]: {type(e).__name__}: {e}")
        raise


def get_config_manager() -> Optional[ConfigManager]:
    """获取配置管理器实例，如果未初始化则尝试自动初始化"""
    global config_manager
    if config_manager is None and _base_dir is not None:
        logger.warning("config_manager 未初始化，尝试自动初始化")
        try:
            config_manager = ConfigManager(_base_dir)
            logger.info(f"config_manager 自动初始化成功: {_base_dir}")
        except Exception as e:
            logger.error(f"config_manager 自动初始化失败: {e}")
    return config_manager
