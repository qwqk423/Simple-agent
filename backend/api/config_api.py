"""配置管理 API"""
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

from config import get_config_manager
from utils.logger import get_logger

logger = get_logger("ConfigAPI")

router = APIRouter()

# 支持的模型类型
ModelType = Literal["llm", "embedding", "rerank"]


def _check_config():
    """检查配置管理器是否可用"""
    global config_manager
    config_manager = get_config_manager()
    if not config_manager:
        logger.error("配置管理器未初始化")
        raise HTTPException(status_code=500, detail="配置管理器未初始化")


class RagModeRequest(BaseModel):
    """RAG 模式请求"""
    enabled: bool


class LLMParamsRequest(BaseModel):
    """LLM 参数请求"""
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    max_tokens: Optional[int] = None
    thinking_enabled: Optional[bool] = None


# ==================== 模型配置相关模型 ====================

class ModelConfigRequest(BaseModel):
    """模型配置请求"""
    name: str = Field(..., min_length=1, max_length=100, description="模型显示名称")
    model: str = Field(..., min_length=1, max_length=100, description="模型ID/名称")
    api_key: str = Field(..., min_length=1, description="API Key")
    base_url: str = Field(..., min_length=1, description="API Base URL")
    is_default: bool = Field(default=False, description="是否为默认模型")


class ModelConfigUpdateRequest(BaseModel):
    """模型配置更新请求"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    model: Optional[str] = Field(default=None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(default=None, min_length=1)
    base_url: Optional[str] = Field(default=None, min_length=1)
    is_default: Optional[bool] = None


class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    id: str
    name: str
    model: str
    api_key: str
    base_url: str
    is_default: bool


class ModelListResponse(BaseModel):
    """模型列表响应"""
    models: List[ModelConfigResponse]
    current_model_id: Optional[str] = None


class CurrentModelRequest(BaseModel):
    """切换当前模型请求"""
    model_config = {'protected_namespaces': ()}
    model_id: str


class TestModelRequest(BaseModel):
    """测试模型连接请求"""
    model: str
    api_key: str
    base_url: str


class TestModelResponse(BaseModel):
    """测试模型连接响应"""
    success: bool
    message: str


# ==================== 原有接口 ====================

@router.get("/config/rag-mode")
async def get_rag_mode():
    """获取 RAG 模式状态"""
    try:
        _check_config()
        logger.debug(f"获取RAG模式状态: {config_manager.rag_mode}")
        return {"enabled": config_manager.rag_mode}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取RAG模式状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取RAG模式状态失败: {str(e)}")


@router.put("/config/rag-mode")
async def set_rag_mode(request: RagModeRequest):
    """设置 RAG 模式"""
    try:
        _check_config()
        old_value = config_manager.rag_mode
        config_manager.rag_mode = request.enabled
        
        if old_value != request.enabled:
            logger.info(f"RAG模式已更改: {old_value} -> {request.enabled}")
        else:
            logger.debug(f"RAG模式保持不变: {request.enabled}")
        
        return {"enabled": request.enabled}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置RAG模式失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置RAG模式失败: {str(e)}")


@router.get("/config/llm-params")
async def get_llm_params():
    """获取 LLM 参数"""
    try:
        _check_config()
        logger.debug("获取LLM参数")
        return config_manager.llm_params
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取LLM参数失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取LLM参数失败: {str(e)}")


@router.put("/config/llm-params")
async def set_llm_params(request: LLMParamsRequest):
    """设置 LLM 参数"""
    try:
        _check_config()
        
        # 获取所有字段，包括显式设置为 false 的布尔值
        data = request.model_dump()
        
        updates = {}
        errors = []
        
        for key, value in data.items():
            # 只处理非 None 的值（包括显式设置的 false）
            if value is not None:
                try:
                    old_value = config_manager.llm_params.get(key)
                    config_manager.update_llm_param(key, value)
                    updates[key] = value
                    
                    # 记录参数变化
                    if old_value != value:
                        logger.debug(f"LLM参数更新: {key} = {value} (原值: {old_value})")
                except Exception as e:
                    errors.append(f"{key}: {str(e)}")
                    logger.warning(f"更新LLM参数失败 [{key}={value}]: {e}")
        
        if errors:
            logger.error(f"部分LLM参数更新失败: {errors}")
            raise HTTPException(status_code=400, detail=f"部分参数更新失败: {'; '.join(errors)}")
        
        if updates:
            logger.info(f"LLM参数已更新: {list(updates.keys())}")
        
        logger.debug(f"配置更新详情: {updates}")
        
        return {"success": True, "updated": updates, "params": config_manager.llm_params}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置LLM参数失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置LLM参数失败: {str(e)}")


# ==================== 模型配置管理接口 ====================

@router.get("/config/{model_type}/models", response_model=ModelListResponse)
async def get_models(
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank")
):
    """获取指定类型的所有模型配置"""
    try:
        _check_config()
        logger.debug(f"获取 {model_type} 模型列表")
        
        models = config_manager.get_models(model_type)
        current_id = config_manager._get_current_model_id(model_type)
        
        return {
            "models": models,
            "current_model_id": current_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {model_type} 模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@router.get("/config/{model_type}/models/{model_id}", response_model=ModelConfigResponse)
async def get_model(
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank"),
    model_id: str = Path(..., description="模型ID")
):
    """获取指定模型配置"""
    try:
        _check_config()
        logger.debug(f"获取 {model_type} 模型: {model_id}")
        
        model = config_manager.get_model(model_type, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="模型不存在")
        
        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {model_type} 模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型失败: {str(e)}")


@router.post("/config/{model_type}/models", response_model=ModelConfigResponse)
async def add_model(
    request: ModelConfigRequest,
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank")
):
    """添加新模型配置"""
    try:
        _check_config()
        logger.info(f"添加 {model_type} 模型: {request.name}")
        
        model_config = request.model_dump()
        result = config_manager.add_model(model_type, model_config)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加 {model_type} 模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加模型失败: {str(e)}")


@router.put("/config/{model_type}/models/{model_id}", response_model=ModelConfigResponse)
async def update_model(
    request: ModelConfigUpdateRequest,
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank"),
    model_id: str = Path(..., description="模型ID")
):
    """更新模型配置"""
    try:
        _check_config()
        logger.info(f"更新 {model_type} 模型: {model_id}")
        
        # 过滤掉 None 值
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")
        
        result = config_manager.update_model(model_type, model_id, updates)
        if not result:
            raise HTTPException(status_code=404, detail="模型不存在")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新 {model_type} 模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新模型失败: {str(e)}")


@router.delete("/config/{model_type}/models/{model_id}")
async def delete_model(
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank"),
    model_id: str = Path(..., description="模型ID")
):
    """删除模型配置"""
    try:
        _check_config()
        logger.info(f"删除 {model_type} 模型: {model_id}")
        
        success = config_manager.delete_model(model_type, model_id)
        if not success:
            raise HTTPException(status_code=400, detail="删除失败，不能删除唯一的模型或模型不存在")
        
        return {"success": True, "message": "模型已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 {model_type} 模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除模型失败: {str(e)}")


@router.put("/config/{model_type}/models/{model_id}/default")
async def set_default_model(
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank"),
    model_id: str = Path(..., description="模型ID")
):
    """设置默认模型"""
    try:
        _check_config()
        logger.info(f"设置默认 {model_type} 模型: {model_id}")
        
        success = config_manager.set_default_model(model_type, model_id)
        if not success:
            raise HTTPException(status_code=404, detail="模型不存在")
        
        return {"success": True, "message": "默认模型已设置"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置默认 {model_type} 模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置默认模型失败: {str(e)}")


@router.get("/config/{model_type}/current")
async def get_current_model(
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank")
):
    """获取当前使用的模型配置（API Key 脱敏）"""
    try:
        _check_config()
        logger.debug(f"获取当前 {model_type} 模型")
        
        model = config_manager.get_current_model(model_type)
        if not model:
            raise HTTPException(status_code=404, detail="没有可用的模型配置")
        
        # 脱敏 API Key
        return config_manager._mask_api_key(model)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前 {model_type} 模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取当前模型失败: {str(e)}")


@router.put("/config/{model_type}/current")
async def set_current_model(
    request: CurrentModelRequest,
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank")
):
    """切换当前使用的模型"""
    try:
        _check_config()
        logger.info(f"切换 {model_type} 模型: {request.model_id}")
        
        success = config_manager.set_current_model(model_type, request.model_id)
        if not success:
            raise HTTPException(status_code=404, detail="模型不存在")
        
        return {"success": True, "message": "模型已切换"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换 {model_type} 模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"切换模型失败: {str(e)}")


@router.post("/config/{model_type}/test", response_model=TestModelResponse)
async def test_model_connection(
    request: TestModelRequest,
    model_type: ModelType = Path(..., description="模型类型: llm, embedding, rerank")
):
    """测试模型连接"""
    try:
        _check_config()
        logger.info(f"测试 {model_type} 模型连接: {request.model}")
        
        # 根据模型类型进行不同的测试
        if model_type == "llm":
            success = await _test_llm_connection(request)
        elif model_type == "embedding":
            success = await _test_embedding_connection(request)
        else:  # rerank
            success = await _test_rerank_connection(request)
        
        if success:
            return {"success": True, "message": "连接测试成功"}
        else:
            return {"success": False, "message": "连接测试失败"}
            
    except Exception as e:
        logger.error(f"测试 {model_type} 模型连接失败: {e}")
        return {"success": False, "message": f"连接测试失败: {str(e)}"}


async def _test_llm_connection(request: TestModelRequest) -> bool:
    """测试 LLM 连接"""
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
            temperature=0,
            max_tokens=10
        )
        # 发送简单请求测试连接
        response = llm.invoke("Hello")
        return response is not None
    except Exception as e:
        logger.error(f"LLM 连接测试失败: {e}")
        return False


async def _test_embedding_connection(request: TestModelRequest) -> bool:
    """测试 Embedding 连接"""
    try:
        from langchain_openai import OpenAIEmbeddings
        
        embeddings = OpenAIEmbeddings(
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url
        )
        # 测试嵌入
        result = embeddings.embed_query("test")
        return result is not None and len(result) > 0
    except Exception as e:
        logger.error(f"Embedding 连接测试失败: {e}")
        return False


async def _test_rerank_connection(request: TestModelRequest) -> bool:
    """测试 Rerank 连接"""
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=request.api_key,
            base_url=request.base_url
        )
        # 测试 rerank API 调用
        response = client.post(
            "/rerank",
            json={
                "model": request.model,
                "query": "test query",
                "documents": ["test document"]
            }
        )
        return response is not None
    except Exception as e:
        logger.error(f"Rerank 连接测试失败: {e}")
        return False
