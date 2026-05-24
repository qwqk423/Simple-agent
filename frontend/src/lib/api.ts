/** API 客户端 */

import {
  Session,
  SessionHistory,
  Message,
  ToolCall,
  Skill,
  FileContent,
  TokenInfo,
  CompressPreviewResponse,
  CompressExecuteResponse,
  TodoItem,
  LLMParams,
  SSEEvent,
  SSEEventType,
  ModelType,
  ModelConfig,
  ModelListResponse,
  ModelConfigRequest,
  TestModelResponse
} from './types';
import { getLogger } from './logger';

const logger = getLogger('API');

export type {
  Session,
  SessionHistory,
  Message,
  ToolCall,
  Skill,
  FileContent,
  TokenInfo,
  CompressPreviewResponse,
  CompressExecuteResponse,
  TodoItem,
  LLMParams,
  SSEEvent,
  SSEEventType
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL 
  || (typeof window !== 'undefined' 
    ? `${window.location.protocol}//${window.location.hostname}:8002`
    : 'http://localhost:8002');

// API 错误类
class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public responseData?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// 辅助函数：处理 API 响应
async function handleResponse<T>(response: Response, context: string): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    let errorData = null;
    
    try {
      errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch (e) {
      // 响应体不是 JSON，使用默认错误信息
    }
    
    logger.error(`${context} 失败`, new APIError(errorMessage, response.status, errorData));
    throw new APIError(errorMessage, response.status, errorData);
  }
  
  const data = await response.json();
  return data;
}

// API 函数

export async function listSessions(): Promise<Session[]> {
  logger.logApiCall('GET', '/api/sessions');
  try {
    const res = await fetch(`${API_BASE}/api/sessions`);
    const data = await handleResponse<{ sessions: Session[] }>(res, '获取会话列表');
    logger.logApiResponse('GET', '/api/sessions', 200, { count: data.sessions.length });
    return data.sessions;
  } catch (err) {
    logger.error('获取会话列表失败', err);
    throw err;
  }
}

export async function createSession(): Promise<Session> {
  logger.logApiCall('POST', '/api/sessions');
  try {
    const res = await fetch(`${API_BASE}/api/sessions`, { method: 'POST' });
    const data = await handleResponse<Session>(res, '创建会话');
    logger.logApiResponse('POST', '/api/sessions', 201, { id: data.id });
    return data;
  } catch (err) {
    logger.error('创建会话失败', err);
    throw err;
  }
}

export async function renameSession(sessionId: string, title: string): Promise<void> {
  logger.logApiCall('PUT', `/api/sessions/${sessionId}`, { title });
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    await handleResponse<void>(res, '重命名会话');
    logger.logApiResponse('PUT', `/api/sessions/${sessionId}`, 200);
  } catch (err) {
    logger.error(`重命名会话失败: ${sessionId}`, err);
    throw err;
  }
}

export async function deleteSession(sessionId: string): Promise<void> {
  logger.logApiCall('DELETE', `/api/sessions/${sessionId}`);
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: 'DELETE' });
    await handleResponse<void>(res, '删除会话');
    logger.logApiResponse('DELETE', `/api/sessions/${sessionId}`, 200);
  } catch (err) {
    logger.error(`删除会话失败: ${sessionId}`, err);
    throw err;
  }
}

export async function getSessionHistory(sessionId: string): Promise<SessionHistory> {
  logger.logApiCall('GET', `/api/sessions/${sessionId}/history`);
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/history`);
    const data = await handleResponse<SessionHistory>(res, '获取会话历史');
    logger.logApiResponse('GET', `/api/sessions/${sessionId}/history`, 200, { 
      messageCount: data.messages?.length 
    });
    return data;
  } catch (err) {
    logger.error(`获取会话历史失败: ${sessionId}`, err);
    throw err;
  }
}

// 压缩相关 API

export async function getCompressPreview(sessionId: string): Promise<CompressPreviewResponse> {
  logger.logApiCall('GET', `/api/sessions/${sessionId}/compress/preview`);
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/compress/preview`);
    const data = await handleResponse<CompressPreviewResponse>(res, '获取压缩预览');
    logger.logApiResponse('GET', `/api/sessions/${sessionId}/compress/preview`, 200, {
      canCompress: data.can_compress,
      newMessagesCount: data.new_messages_count
    });
    return data;
  } catch (err) {
    logger.error(`获取压缩预览失败: ${sessionId}`, err);
    throw err;
  }
}

export async function executeCompress(sessionId: string): Promise<CompressExecuteResponse> {
  logger.logApiCall('POST', `/api/sessions/${sessionId}/compress`);
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/compress`, { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true })
    });
    const data = await handleResponse<CompressExecuteResponse>(res, '执行压缩');
    logger.logApiResponse('POST', `/api/sessions/${sessionId}/compress`, 200, {
      compressedCount: data.compressed_count,
      compressedRounds: data.compressed_rounds
    });
    return data;
  } catch (err) {
    logger.error(`执行压缩失败: ${sessionId}`, err);
    throw err;
  }
}

// 兼容旧 API（已废弃，保留用于过渡）
export async function compressSession(sessionId: string): Promise<any> {
  logger.warn('compressSession 已废弃，请使用 executeCompress');
  return executeCompress(sessionId);
}

export async function listSkills(): Promise<Skill[]> {
  logger.logApiCall('GET', '/api/skills');
  try {
    const res = await fetch(`${API_BASE}/api/skills`);
    const data = await handleResponse<{ skills: Skill[] }>(res, '获取技能列表');
    logger.logApiResponse('GET', '/api/skills', 200, { count: data.skills.length });
    return data.skills;
  } catch (err) {
    logger.error('获取技能列表失败', err);
    throw err;
  }
}

export async function readFile(path: string): Promise<FileContent> {
  logger.logApiCall('GET', `/api/files?path=${path}`);
  try {
    const res = await fetch(`${API_BASE}/api/files?path=${encodeURIComponent(path)}`);
    const data = await handleResponse<FileContent>(res, '读取文件');
    logger.logApiResponse('GET', `/api/files`, 200, { path, size: data.content?.length });
    return data;
  } catch (err) {
    logger.error(`读取文件失败: ${path}`, err);
    throw err;
  }
}

export async function saveFile(path: string, content: string): Promise<void> {
  logger.logApiCall('POST', '/api/files', { path, contentLength: content.length });
  try {
    const res = await fetch(`${API_BASE}/api/files`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content }),
    });
    await handleResponse<void>(res, '保存文件');
    logger.logApiResponse('POST', '/api/files', 200, { path });
  } catch (err) {
    logger.error(`保存文件失败: ${path}`, err);
    throw err;
  }
}

export async function getSessionTokens(sessionId: string): Promise<any> {
  logger.logApiCall('GET', `/api/tokens/session/${sessionId}`);
  try {
    const res = await fetch(`${API_BASE}/api/tokens/session/${sessionId}`);
    const data = await handleResponse<any>(res, '获取会话 Token');
    logger.logApiResponse('GET', `/api/tokens/session/${sessionId}`, 200);
    return data;
  } catch (err) {
    logger.error(`获取会话 Token 失败: ${sessionId}`, err);
    throw err;
  }
}

export async function getRagMode(): Promise<boolean> {
  logger.logApiCall('GET', '/api/config/rag-mode');
  try {
    const res = await fetch(`${API_BASE}/api/config/rag-mode`);
    const data = await handleResponse<{ enabled: boolean }>(res, '获取 RAG 模式');
    logger.logApiResponse('GET', '/api/config/rag-mode', 200, { enabled: data.enabled });
    return data.enabled;
  } catch (err) {
    logger.error('获取 RAG 模式失败', err);
    throw err;
  }
}

export async function setRagMode(enabled: boolean): Promise<void> {
  logger.logApiCall('PUT', '/api/config/rag-mode', { enabled });
  try {
    const res = await fetch(`${API_BASE}/api/config/rag-mode`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
    await handleResponse<void>(res, '设置 RAG 模式');
    logger.logApiResponse('PUT', '/api/config/rag-mode', 200, { enabled });
  } catch (err) {
    logger.error('设置 RAG 模式失败', err);
    throw err;
  }
}

export async function getLLMParams(): Promise<LLMParams> {
  logger.logApiCall('GET', '/api/config/llm-params');
  try {
    const res = await fetch(`${API_BASE}/api/config/llm-params`);
    const data = await handleResponse<LLMParams>(res, '获取 LLM 参数');
    logger.logApiResponse('GET', '/api/config/llm-params', 200);
    return data;
  } catch (err) {
    logger.error('获取 LLM 参数失败', err);
    throw err;
  }
}

export async function setLLMParams(params: Partial<LLMParams>): Promise<{ success: boolean; updated: Partial<LLMParams>; params: LLMParams }> {
  logger.logApiCall('PUT', '/api/config/llm-params', params);
  try {
    const res = await fetch(`${API_BASE}/api/config/llm-params`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    const data = await handleResponse<{ success: boolean; updated: Partial<LLMParams>; params: LLMParams }>(res, '设置 LLM 参数');
    logger.logApiResponse('PUT', '/api/config/llm-params', 200);
    return data;
  } catch (err) {
    logger.error('设置 LLM 参数失败', err);
    throw err;
  }
}

// ==================== 模型配置管理 API ====================

export async function getModels(modelType: ModelType): Promise<ModelListResponse> {
  logger.logApiCall('GET', `/api/config/${modelType}/models`);
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/models`);
    const data = await handleResponse<ModelListResponse>(res, `获取 ${modelType} 模型列表`);
    logger.logApiResponse('GET', `/api/config/${modelType}/models`, 200, { count: data.models.length });
    return data;
  } catch (err) {
    logger.error(`获取 ${modelType} 模型列表失败`, err);
    throw err;
  }
}

export async function getModel(modelType: ModelType, modelId: string): Promise<ModelConfig> {
  logger.logApiCall('GET', `/api/config/${modelType}/models/${modelId}`);
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/models/${modelId}`);
    const data = await handleResponse<ModelConfig>(res, `获取 ${modelType} 模型`);
    logger.logApiResponse('GET', `/api/config/${modelType}/models/${modelId}`, 200);
    return data;
  } catch (err) {
    logger.error(`获取 ${modelType} 模型失败`, err);
    throw err;
  }
}

export async function addModel(modelType: ModelType, config: ModelConfigRequest): Promise<ModelConfig> {
  logger.logApiCall('POST', `/api/config/${modelType}/models`, config);
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/models`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    const data = await handleResponse<ModelConfig>(res, `添加 ${modelType} 模型`);
    logger.logApiResponse('POST', `/api/config/${modelType}/models`, 200, { id: data.id });
    return data;
  } catch (err) {
    logger.error(`添加 ${modelType} 模型失败`, err);
    throw err;
  }
}

export async function updateModel(modelType: ModelType, modelId: string, config: Partial<ModelConfigRequest>): Promise<ModelConfig> {
  logger.logApiCall('PUT', `/api/config/${modelType}/models/${modelId}`, config);
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/models/${modelId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    const data = await handleResponse<ModelConfig>(res, `更新 ${modelType} 模型`);
    logger.logApiResponse('PUT', `/api/config/${modelType}/models/${modelId}`, 200);
    return data;
  } catch (err) {
    logger.error(`更新 ${modelType} 模型失败`, err);
    throw err;
  }
}

export async function deleteModel(modelType: ModelType, modelId: string): Promise<{ success: boolean; message: string }> {
  logger.logApiCall('DELETE', `/api/config/${modelType}/models/${modelId}`);
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/models/${modelId}`, {
      method: 'DELETE',
    });
    const data = await handleResponse<{ success: boolean; message: string }>(res, `删除 ${modelType} 模型`);
    logger.logApiResponse('DELETE', `/api/config/${modelType}/models/${modelId}`, 200);
    return data;
  } catch (err) {
    logger.error(`删除 ${modelType} 模型失败`, err);
    throw err;
  }
}

export async function setDefaultModel(modelType: ModelType, modelId: string): Promise<{ success: boolean; message: string }> {
  logger.logApiCall('PUT', `/api/config/${modelType}/models/${modelId}/default`);
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/models/${modelId}/default`, {
      method: 'PUT',
    });
    const data = await handleResponse<{ success: boolean; message: string }>(res, `设置默认 ${modelType} 模型`);
    logger.logApiResponse('PUT', `/api/config/${modelType}/models/${modelId}/default`, 200);
    return data;
  } catch (err) {
    logger.error(`设置默认 ${modelType} 模型失败`, err);
    throw err;
  }
}

export async function getCurrentModel(modelType: ModelType): Promise<ModelConfig> {
  logger.logApiCall('GET', `/api/config/${modelType}/current`);
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/current`);
    const data = await handleResponse<ModelConfig>(res, `获取当前 ${modelType} 模型`);
    logger.logApiResponse('GET', `/api/config/${modelType}/current`, 200);
    return data;
  } catch (err) {
    logger.error(`获取当前 ${modelType} 模型失败`, err);
    throw err;
  }
}

export async function setCurrentModel(modelType: ModelType, modelId: string): Promise<{ success: boolean; message: string }> {
  logger.logApiCall('PUT', `/api/config/${modelType}/current`, { model_id: modelId });
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/current`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId }),
    });
    const data = await handleResponse<{ success: boolean; message: string }>(res, `切换 ${modelType} 模型`);
    logger.logApiResponse('PUT', `/api/config/${modelType}/current`, 200);
    return data;
  } catch (err) {
    logger.error(`切换 ${modelType} 模型失败`, err);
    throw err;
  }
}

export async function testModelConnection(
  modelType: ModelType,
  config: { model: string; api_key: string; base_url: string }
): Promise<TestModelResponse> {
  logger.logApiCall('POST', `/api/config/${modelType}/test`, config);
  try {
    const res = await fetch(`${API_BASE}/api/config/${modelType}/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    const data = await handleResponse<TestModelResponse>(res, `测试 ${modelType} 模型连接`);
    logger.logApiResponse('POST', `/api/config/${modelType}/test`, 200, { success: data.success });
    return data;
  } catch (err) {
    logger.error(`测试 ${modelType} 模型连接失败`, err);
    throw err;
  }
}

// 获取最后一次发送给 LLM 的请求
export async function getLastRequest(): Promise<{ success: boolean; message?: string; request: any }> {
  logger.logApiCall('GET', '/api/chat/last-request');
  try {
    const res = await fetch(`${API_BASE}/api/chat/last-request`);
    const data = await handleResponse<{ success: boolean; message?: string; request: any }>(res, '获取最后请求');
    logger.logApiResponse('GET', '/api/chat/last-request', 200, { success: data.success });
    return data;
  } catch (err) {
    logger.error('获取最后请求失败', err);
    throw err;
  }
}

// SSE 流式聊天
export function streamChat(
  message: string,
  sessionId: string,
  images: string[] = [],
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void
): () => void {
  logger.group('SSE 流式聊天', true);
  logger.info(`启动流式聊天: sessionId=${sessionId}`, { 
    messageLength: message.length, 
    imageCount: images.length 
  });
  
  const controller = new AbortController();

  fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, images, stream: true }),
    signal: controller.signal,
  }).then(async (res) => {
    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch (e) {
        // 忽略解析错误
      }
      throw new APIError(errorMessage, res.status);
    }
    
    logger.info('SSE 连接已建立');
    
    const reader = res.body?.getReader();
    if (!reader) {
      throw new Error('无法获取响应流');
    }
    
    const decoder = new TextDecoder();
    let buffer = '';
    let eventCount = 0;
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          logger.info(`SSE 流结束，共接收 ${eventCount} 个事件`);
          break;
        }
        
        buffer += decoder.decode(value, { stream: true });
        
        // 解析 SSE 事件
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        let currentEvent: string | null = null;
        let currentData: string = '';
        
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7);
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6);
          } else if (line === '' && currentEvent) {
            try {
              const data = JSON.parse(currentData);
              eventCount++;
              
              // 只在开发模式下记录详细事件
              if (process.env.NODE_ENV === 'development') {
                if (['tool_start', 'tool_end', 'error', 'done'].includes(currentEvent)) {
                  logger.debug(`SSE 事件: ${currentEvent}`, data);
                }
              }
              
              onEvent({ type: currentEvent as SSEEventType, data });
            } catch (e) {
              logger.error('解析 SSE 数据失败', e, { raw: currentData });
            }
            currentEvent = null;
            currentData = '';
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        logger.info('SSE 连接被用户中断');
      } else {
        logger.error('读取 SSE 流失败', err);
        if (onError) {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
      }
    } finally {
      reader.releaseLock();
      logger.groupEnd();
    }
  }).catch((err) => {
    // 这是最外层的错误捕获，处理 fetch 本身的错误
    // 忽略 AbortError（用户主动中断是正常的操作）
    if (err instanceof Error && err.name === 'AbortError') {
      logger.info('SSE 请求被取消');
      logger.groupEnd();
      return;
    }
    
    logger.error('SSE 流式聊天失败', err);
    logger.groupEnd();
    
    if (onError) {
      onError(err instanceof Error ? err : new Error(String(err)));
    }
  });
  
  return () => {
    logger.debug('取消 SSE 请求');
    controller.abort();
  };
}
