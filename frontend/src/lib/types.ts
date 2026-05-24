/** 共享类型定义 */

// 会话相关
export interface Session {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

export interface SessionHistory {
  session_id: string;
  title: string;
  created_at: number;
  updated_at: number;
  compressed_context: string;
  compressed_rounds: number;
  last_compressed_index: number;
  messages: Message[];
}

// 消息相关
export interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  images?: string[];
  tool_calls?: ToolCall[];
  tool_call_id?: string;
}

// 工具调用
export interface ToolCall {
  id: string;
  tool: string;
  input: any;
  output?: string;
  status?: 'running' | 'success' | 'error';
  duration?: number;
  startTime?: number;
}

// 技能相关
export interface Skill {
  name: string;
  description: string;
  location: string;
}

// 文件相关
export interface FileContent {
  path: string;
  content: string;
}

// Token 统计
export interface TokenInfo {
  path: string;
  exists: boolean;
  chars: number;
  tokens: number;
}

// 压缩相关
export interface CompressPreviewResponse {
  session_id: string;
  new_messages_count: number;
  total_messages_count: number;
  request_detail: string;
  can_compress: boolean;
}

export interface CompressExecuteResponse {
  session_id: string;
  compressed_count: number;
  compressed_rounds: number;
  merged: boolean;
  merged_rounds: number | null;
  summary: string;
}

// 待办事项
export interface TodoItem {
  id: string;
  content: string;
  status: "pending" | "in_progress" | "completed" | "blocked";
  priority: "high" | "medium" | "low";
}

// LLM 参数
export interface LLMParams {
  temperature: number;
  top_p: number;
  presence_penalty: number;
  max_tokens: number;
  thinking_enabled: boolean;
}

// SSE 事件
export type SSEEventType = 
  | 'retrieval'
  | 'token'
  | 'tool_start'
  | 'tool_end'
  | 'todo_update'
  | 'done'
  | 'title'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  data: any;
}

// ==================== 模型配置相关类型 ====================

// 模型类型
export type ModelType = 'llm' | 'embedding' | 'rerank';

// 单个模型配置
export interface ModelConfig {
  id: string;
  name: string;
  model: string;
  api_key: string;
  base_url: string;
  is_default: boolean;
}

// 模型列表响应
export interface ModelListResponse {
  models: ModelConfig[];
  current_model_id: string | null;
}

// 模型配置请求（添加/更新）
export interface ModelConfigRequest {
  name: string;
  model: string;
  api_key: string;
  base_url: string;
  is_default?: boolean;
}

// 测试模型连接响应
export interface TestModelResponse {
  success: boolean;
  message: string;
}
