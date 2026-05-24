/** React Context 状态管理 */
"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, useRef, ReactNode } from 'react';
import * as api from './api';
import { TodoItem, ToolCall, LLMParams, CompressPreviewResponse, ModelType, ModelConfig } from './types';
import { getLogger } from './logger';

const logger = getLogger('Store');

// 前端扩展类型（在共享类型基础上扩展）
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  images?: string[];
  thinking?: string;
  toolCalls?: ToolCall[];
  retrievals?: any[];
  todos?: TodoItem[];
  timestamp: number;
}

export interface Session {
  id: string;
  title: string;
  updatedAt: number;
  messageCount: number;
}

// 压缩预览状态
export interface CompressPreviewState {
  isOpen: boolean;
  isLoading: boolean;
  previewData: CompressPreviewResponse | null;
  error: string | null;
}

// LLM 参数默认值
export const DEFAULT_LLM_PARAMS: LLMParams = {
  temperature: 0.7,
  top_p: 0.8,
  presence_penalty: 0.0,
  max_tokens: 4096,
  thinking_enabled: true,
};

export type Theme = 'light' | 'dark' | 'system';

// 模型配置状态
interface ModelConfigState {
  llmModels: ModelConfig[];
  embeddingModels: ModelConfig[];
  rerankModels: ModelConfig[];
  currentLLMModelId: string | null;
  currentEmbeddingModelId: string | null;
  currentRerankModelId: string | null;
  isLoading: boolean;
}

interface AppState {
  sessions: Session[];
  currentSessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  sidebarWidth: number;
  inspectorWidth: number;
  inspectorTab: 'memory' | 'skills' | 'files' | 'settings' | 'models';
  inspectorFilePath: string | null;
  ragMode: boolean;
  llmParams: LLMParams;
  showThinking: boolean;  // 思考过程显示开关
  lastRequest: any | null;  // 最后一次发送给 LLM 的请求
  showRequestViewer: boolean;  // 是否显示请求查看器
  theme: Theme;
  isDark: boolean;
  // 压缩预览状态
  compressPreview: CompressPreviewState;
  // 模型配置状态
  modelConfigs: ModelConfigState;
  
  loadSessions: () => Promise<void>;
  createSession: () => Promise<string | null>;
  selectSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, title: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  sendMessage: (content: string, images?: string[]) => Promise<void>;
  stopStreaming: () => void;
  // 压缩相关
  openCompressPreview: () => Promise<void>;
  closeCompressPreview: () => void;
  executeCompress: () => Promise<void>;
  compressSession: () => Promise<void>; // 兼容旧方法
  toggleRagMode: () => Promise<void>;
  setInspectorTab: (tab: 'memory' | 'skills' | 'files' | 'settings' | 'models') => void;
  setInspectorFilePath: (path: string | null) => void;
  setSidebarWidth: (width: number) => void;
  setInspectorWidth: (width: number) => void;
  updateLLMParam: (key: keyof LLMParams, value: number | boolean) => Promise<void>;
  loadLLMParams: () => Promise<void>;
  toggleShowThinking: () => void;
  loadLastRequest: () => Promise<void>;
  toggleRequestViewer: () => void;
  closeRequestViewer: () => void;
  setTheme: (theme: Theme) => void;
  // 模型配置相关
  loadModelConfigs: () => Promise<void>;
  addModelConfig: (modelType: ModelType, config: { name: string; model: string; api_key: string; base_url: string; is_default?: boolean }) => Promise<ModelConfig | null>;
  updateModelConfig: (modelType: ModelType, modelId: string, config: Partial<{ name: string; model: string; api_key: string; base_url: string; is_default?: boolean }>) => Promise<ModelConfig | null>;
  deleteModelConfig: (modelType: ModelType, modelId: string) => Promise<boolean>;
  setCurrentModel: (modelType: ModelType, modelId: string) => Promise<boolean>;
  setDefaultModel: (modelType: ModelType, modelId: string) => Promise<boolean>;
  testModelConnection: (modelType: ModelType, config: { model: string; api_key: string; base_url: string }) => Promise<{ success: boolean; message: string }>;
}

const AppContext = createContext<AppState | null>(null);

// 解析 think 标签
function parseThinkContent(raw: string): { content: string; thinking: string } {
  // 匹配完整的 think 标签
  const thinkMatch = raw.match(/<think>([\s\S]*?)<\/think>/);
  if (thinkMatch) {
    return {
      thinking: thinkMatch[1].trim(),
      content: raw.replace(/<think>[\s\S]*?<\/think>/, '').trim()
    };
  }
  // 流式：未闭合的 think 标签
  if (raw.includes('<think>')) {
    const startIdx = raw.indexOf('<think>');
    const endIdx = raw.indexOf('</think>');
    if (endIdx === -1) {
      return { 
        thinking: raw.slice(startIdx + 7), 
        content: raw.slice(0, startIdx).trim() 
      };
    }
  }
  return { content: raw, thinking: '' };
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [inspectorWidth, setInspectorWidth] = useState(400);
  const [inspectorTab, setInspectorTab] = useState<'memory' | 'skills' | 'files' | 'settings' | 'models'>('memory');
  const [inspectorFilePath, setInspectorFilePath] = useState<string | null>(null);
  const [ragMode, setRagMode] = useState(false);
  const [llmParams, setLLMParams] = useState<LLMParams>(DEFAULT_LLM_PARAMS);
  const [showThinking, setShowThinking] = useState(() => {
    if (typeof window === 'undefined') return true;
    const saved = localStorage.getItem('showThinking');
    return saved ? saved === 'true' : true;
  });
  const [lastRequest, setLastRequest] = useState<any | null>(null);
  const [showRequestViewer, setShowRequestViewer] = useState(false);
  
  // 压缩预览状态
  const [compressPreview, setCompressPreview] = useState<CompressPreviewState>({
    isOpen: false,
    isLoading: false,
    previewData: null,
    error: null
  });

  // 模型配置状态
  const [modelConfigs, setModelConfigs] = useState<ModelConfigState>({
    llmModels: [],
    embeddingModels: [],
    rerankModels: [],
    currentLLMModelId: null,
    currentEmbeddingModelId: null,
    currentRerankModelId: null,
    isLoading: false,
  });
  
  // 主题状态
  const [theme, setThemeState] = useState<Theme>('system');
  const [isDark, setIsDark] = useState(false);
  
  // 用于中断流式请求的 ref
  const abortControllerRef = useRef<(() => void) | null>(null);
  
  // 检测系统主题偏好
  const getSystemTheme = useCallback(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }, []);
  
  // 应用主题
  const applyTheme = useCallback((newTheme: Theme) => {
    const root = document.documentElement;
    const shouldBeDark = newTheme === 'dark' || (newTheme === 'system' && getSystemTheme());
    
    if (shouldBeDark) {
      root.classList.add('dark');
      setIsDark(true);
    } else {
      root.classList.remove('dark');
      setIsDark(false);
    }
    logger.debug(`主题应用: ${newTheme}, 暗黑模式: ${shouldBeDark}`);
  }, [getSystemTheme]);
  
  // 设置主题
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
    applyTheme(newTheme);
    logger.info(`主题已切换为: ${newTheme}`);
  }, [applyTheme]);
  
  // 初始化主题
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem('theme') as Theme | null;
      const initialTheme = savedTheme || 'system';
      setThemeState(initialTheme);
      applyTheme(initialTheme);
      logger.info(`主题初始化完成: ${initialTheme}`);
      
      // 监听系统主题变化
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        if (theme === 'system') {
          applyTheme('system');
        }
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } catch (err) {
      logger.error('主题初始化失败', err);
    }
  }, [applyTheme, theme]);

  const loadSessions = useCallback(async () => {
    logger.info('开始加载会话列表...');
    try {
      const data = await api.listSessions();
      const mappedSessions = data.map(s => ({
        id: s.id,
        title: s.title || '新对话',
        updatedAt: s.updated_at * 1000,
        messageCount: s.message_count,
      }));
      setSessions(mappedSessions);
      logger.info(`会话列表加载完成: ${mappedSessions.length} 个会话`);
    } catch (err) {
      logger.error('加载会话列表失败', err);
    }
  }, []);

  const createSession = useCallback(async (): Promise<string | null> => {
    logger.info('创建新会话...');
    try {
      const session = await api.createSession();
      const newSession: Session = {
        id: session.id,
        title: '新对话',
        updatedAt: Date.now(),
        messageCount: 0,
      };
      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(session.id);
      setMessages([]);
      logger.info(`新会话创建成功: ${session.id}`);
      return session.id;
    } catch (err) {
      logger.error('创建会话失败', err);
      return null;
    }
  }, []);

  const selectSession = useCallback(async (sessionId: string) => {
    logger.info(`选择会话: ${sessionId}`);
    try {
      const history = await api.getSessionHistory(sessionId);
      setCurrentSessionId(sessionId);
      
      // 收集 tool 消息的输出，按 tool_call_id 索引
      const toolOutputs: Record<string, { output: string; status: 'success' | 'error' }> = {};
      history.messages.forEach(m => {
        if (m.role === 'tool' && m.tool_call_id) {
          toolOutputs[m.tool_call_id] = {
            output: m.content || '',
            status: m.content?.startsWith('[错误]') ? 'error' : 'success',
          };
        }
      });
      
      const convertToolCalls = (toolCalls: any[] | undefined) => {
        if (!toolCalls) return undefined;
        return toolCalls.map(tc => {
          const func = tc.function || {};
          let input = func.arguments;
          if (typeof input === 'string') {
            try {
              input = JSON.parse(input);
            } catch (e) {
              logger.warn(`工具参数解析失败: ${func.name}`, e);
              input = input;
            }
          }
          // 查找对应的 tool 输出
          const toolOutput = toolOutputs[tc.id];
          return {
            id: tc.id,
            tool: func.name || '',
            input: input || {},
            output: toolOutput?.output,
            status: toolOutput?.status,
          };
        });
      };
      
      // 过滤掉 tool 角色消息
      const filteredMessages = history.messages.filter(m => m.role !== 'tool');
      
      // 合并连续的 assistant 消息（工具调用和最终回复可能分开保存）
      const convertedMessages: Message[] = [];
      let currentAssistant: Message | null = null;
      
      for (let i = 0; i < filteredMessages.length; i++) {
        const m = filteredMessages[i];
        
        if (m.role === 'assistant') {
          if (currentAssistant === null) {
            // 第一个 assistant 消息
            currentAssistant = {
              id: `${sessionId}-${i}`,
              role: 'assistant',
              content: m.content || '',
              images: m.images,
              toolCalls: convertToolCalls(m.tool_calls) || [],
              timestamp: Date.now(),
            };
          } else {
            // 连续的 assistant 消息，合并
            if (m.content) {
              currentAssistant.content = currentAssistant.content 
                ? `${currentAssistant.content}\n${m.content}` 
                : m.content;
            }
            const newToolCalls = convertToolCalls(m.tool_calls);
            if (newToolCalls && newToolCalls.length > 0) {
              currentAssistant.toolCalls = [
                ...(currentAssistant.toolCalls || []),
                ...newToolCalls
              ];
            }
          }
        } else {
          // 非 assistant 消息，先保存之前的 assistant 消息
          if (currentAssistant !== null) {
            convertedMessages.push(currentAssistant);
            currentAssistant = null;
          }
          convertedMessages.push({
            id: `${sessionId}-${i}`,
            role: m.role as any,
            content: m.content,
            images: m.images,
            toolCalls: convertToolCalls(m.tool_calls),
            timestamp: Date.now(),
          });
        }
      }
      
      // 保存最后一个 assistant 消息
      if (currentAssistant !== null) {
        convertedMessages.push(currentAssistant);
      }
      
      setMessages(convertedMessages);
      logger.info(`会话历史加载完成: ${convertedMessages.length} 条消息`);
    } catch (err) {
      logger.error(`加载会话历史失败: ${sessionId}`, err);
    }
  }, []);

  const renameSession = useCallback(async (sessionId: string, title: string) => {
    logger.info(`重命名会话: ${sessionId} -> "${title}"`);
    try {
      await api.renameSession(sessionId, title);
      setSessions(prev => prev.map(s => 
        s.id === sessionId ? { ...s, title } : s
      ));
      logger.info('会话重命名成功');
    } catch (err) {
      logger.error('重命名会话失败', err);
    }
  }, []);

  const deleteSession = useCallback(async (sessionId: string) => {
    logger.info(`删除会话: ${sessionId}`);
    try {
      await api.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
        logger.info('当前会话已删除，清空消息列表');
      }
      logger.info('会话删除成功');
    } catch (err) {
      logger.error('删除会话失败', err);
    }
  }, [currentSessionId]);

  const sendMessage = useCallback(async (content: string, images?: string[]) => {
    logger.group('发送消息流程', true);
    
    // 如果没有当前会话，先创建会话
    let sessionId = currentSessionId;
    if (!sessionId) {
      logger.info('无当前会话，先创建新会话');
      const newSessionId = await createSession();
      if (!newSessionId) {
        logger.error('创建会话失败，无法发送消息');
        logger.groupEnd();
        return;
      }
      sessionId = newSessionId;
    }

    setIsStreaming(true);
    logger.info(`开始发送消息到会话: ${sessionId}`, { contentLength: content.length, hasImages: !!images?.length });
    
    // 保存用户消息和助手消息的 ID，用于中断时删除
    const userMessageId = `user-${Date.now()}`;
    const assistantId = `assistant-${Date.now() + 1}`;
    
    // 添加用户消息
    const userMessage: Message = {
      id: userMessageId,
      role: 'user',
      content,
      images,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMessage]);
    logger.debug(`用户消息已添加: ${userMessageId}`);
    
    // 创建助手消息
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      thinking: '',
      toolCalls: [],
      timestamp: Date.now(),
    }]);
    logger.debug(`助手消息占位符已创建: ${assistantId}`);
    
    // 状态跟踪
    let rawContent = '';
    let thinkingContent = '';
    let toolCalls: ToolCall[] = [];
    
    // 启动流式请求并保存取消函数
    const abort = api.streamChat(
      content,
      sessionId,
      images,
      (event) => {
        switch (event.type) {
          case 'token':
            // 处理 reasoning_content (thinking) 和普通 content
            const contentChunk = event.data.content || '';
            const thinkingChunk = event.data.thinking || '';
            
            if (contentChunk) {
              rawContent += contentChunk;
            }
            if (thinkingChunk) {
              thinkingContent += thinkingChunk;
            }
            
            // 如果有原始 thinking，优先使用；否则尝试解析 <think> 标签
            const hasRawThinking = thinkingContent.length > 0;
            const parsed = hasRawThinking 
              ? { content: rawContent, thinking: thinkingContent }
              : parseThinkContent(rawContent);
            
            setMessages(prev => prev.map(m => 
              m.id === assistantId 
                ? { ...m, content: parsed.content, thinking: parsed.thinking }
                : m
            ));
            break;
            
          case 'tool_start': {
            // 添加新工具调用
            const newTool: ToolCall = {
              id: event.data.id || `tc_${toolCalls.length}`,
              tool: event.data.tool,
              input: event.data.input,
              output: '', // 空表示执行中
              status: 'running',
              startTime: Date.now(),
            };
            toolCalls = [...toolCalls, newTool];
            logger.info(`工具调用开始: ${newTool.tool}`, { toolId: newTool.id });
            setMessages(prev => prev.map(m => 
              m.id === assistantId 
                ? { ...m, toolCalls: [...toolCalls] }
                : m
            ));
            break;
          }
            
          case 'tool_end': {
            // 通过 ID 精确匹配更新工具输出
            const toolId = event.data.id;
            const toolName = event.data.tool;
            const output = event.data.output;
            const status = event.data.status || 'success';
            const endTime = Date.now();
            
            logger.info(`工具调用结束: ${toolName}`, { toolId, status });
            
            // 先尝试通过 ID 匹配
            let matched = false;
            toolCalls = toolCalls.map(tc => {
              if (tc.id === toolId && tc.status === 'running') {
                matched = true;
                const duration = tc.startTime ? endTime - tc.startTime : undefined;
                logger.debug(`工具 ${toolName} 执行耗时: ${duration}ms`);
                return { 
                  ...tc, 
                  output, 
                  status,
                  duration
                };
              }
              return tc;
            });
            
            // 如果 ID 匹配失败，退回到名称匹配（兼容模式）
            if (!matched) {
              logger.warn(`工具ID匹配失败，使用名称匹配: ${toolName}`);
              toolCalls = toolCalls.map(tc => 
                tc.tool === toolName && tc.status === 'running'
                  ? { 
                      ...tc, 
                      output, 
                      status,
                      duration: tc.startTime ? endTime - tc.startTime : undefined
                    }
                  : tc
              );
            }
            
            setMessages(prev => prev.map(m => 
              m.id === assistantId 
                ? { ...m, toolCalls: [...toolCalls] }
                : m
            ));
            break;
          }
            
          case 'retrieval':
            logger.info('检索结果更新', { count: event.data.results?.length || 0 });
            setMessages(prev => prev.map(m => 
              m.id === assistantId 
                ? { ...m, retrievals: event.data.results || [] }
                : m
            ));
            break;
            
          case 'todo_update':
            logger.info('待办事项更新', { count: event.data.todos?.length || 0 });
            setMessages(prev => prev.map(m => 
              m.id === assistantId 
                ? { ...m, todos: event.data.todos || [] }
                : m
            ));
            break;
            
          case 'title':
            logger.info(`会话标题更新: "${event.data.title}"`);
            setSessions(prev => prev.map(s => 
              s.id === event.data.session_id 
                ? { ...s, title: event.data.title }
                : s
            ));
            break;
            
          case 'done':
            logger.info('流式响应完成');
            setIsStreaming(false);
            abortControllerRef.current = null;
            loadSessions();
            logger.groupEnd();
            break;
            
          case 'error': {
            // 解析后端错误：可能是 { error: string } 或 { message: string } 格式
            let errorMessage = '未知错误';
            if (event.data && typeof event.data === 'object') {
              if ('error' in event.data && event.data.error) {
                errorMessage = String(event.data.error);
              } else if ('message' in event.data && event.data.message) {
                errorMessage = String(event.data.message);
              } else if (JSON.stringify(event.data) !== '{}') {
                errorMessage = JSON.stringify(event.data);
              }
            } else if (typeof event.data === 'string') {
              errorMessage = event.data;
            }
            logger.error('流式响应出错', new Error(errorMessage), { rawData: event.data });
            setIsStreaming(false);
            abortControllerRef.current = null;
            loadSessions();
            logger.groupEnd();
            break;
          }
        }
      },
      (err) => {
        logger.error('流式请求错误', err);
        setIsStreaming(false);
        abortControllerRef.current = null;
        logger.groupEnd();
      }
    );
    
    // 保存取消函数到 ref
    abortControllerRef.current = () => {
      logger.info('用户中断流式响应');
      abort();
      // 停止生成但保留已生成的内容
      setIsStreaming(false);
      abortControllerRef.current = null;
      logger.groupEnd();
    };
  }, [currentSessionId, createSession, loadSessions]);

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current();
    }
  }, []);

  // ========== 压缩相关方法 ==========
  
  // 打开压缩预览
  const openCompressPreview = useCallback(async () => {
    if (isStreaming) {
      logger.warn('流式响应中，禁止压缩');
      return;
    }
    if (!currentSessionId) {
      logger.warn('无当前会话，无法压缩');
      return;
    }
    
    logger.info(`打开压缩预览: ${currentSessionId}`);
    
    setCompressPreview({
      isOpen: true,
      isLoading: true,
      previewData: null,
      error: null
    });
    
    try {
      const previewData = await api.getCompressPreview(currentSessionId);
      setCompressPreview(prev => ({
        ...prev,
        isLoading: false,
        previewData
      }));
      logger.info('压缩预览数据加载成功', { 
        canCompress: previewData.can_compress,
        newMessagesCount: previewData.new_messages_count
      });
    } catch (err: any) {
      logger.error('获取压缩预览失败', err);
      setCompressPreview(prev => ({
        ...prev,
        isLoading: false,
        error: err.message || '获取压缩预览失败'
      }));
    }
  }, [currentSessionId, isStreaming]);
  
  // 关闭压缩预览
  const closeCompressPreview = useCallback(() => {
    logger.debug('关闭压缩预览');
    setCompressPreview({
      isOpen: false,
      isLoading: false,
      previewData: null,
      error: null
    });
  }, []);
  
  // 执行压缩
  const executeCompress = useCallback(async () => {
    if (!currentSessionId) {
      logger.warn('无当前会话，无法执行压缩');
      return;
    }
    
    logger.info(`执行会话压缩: ${currentSessionId}`);
    setCompressPreview(prev => ({ ...prev, isLoading: true }));
    
    try {
      const result = await api.executeCompress(currentSessionId);
      logger.info('会话压缩成功', { 
        compressedCount: result.compressed_count,
        compressedRounds: result.compressed_rounds 
      });
      
      // 关闭预览
      closeCompressPreview();
      
      // 刷新会话（显示"对话已压缩"提示）
      await selectSession(currentSessionId);
    } catch (err: any) {
      logger.error('执行压缩失败', err);
      setCompressPreview(prev => ({
        ...prev,
        isLoading: false,
        error: err.message || '压缩失败'
      }));
    }
  }, [currentSessionId, closeCompressPreview, selectSession]);
  
  // 兼容旧方法（直接打开预览）
  const compressSession = useCallback(async () => {
    await openCompressPreview();
  }, [openCompressPreview]);

  const toggleRagMode = useCallback(async () => {
    const newMode = !ragMode;
    logger.info(`切换 RAG 模式: ${ragMode} -> ${newMode}`);
    try {
      await api.setRagMode(newMode);
      setRagMode(newMode);
      logger.info('RAG 模式切换成功');
    } catch (err) {
      logger.error('切换 RAG 模式失败', err);
    }
  }, [ragMode]);

  const loadLLMParams = useCallback(async () => {
    logger.info('加载 LLM 参数...');
    try {
      const params = await api.getLLMParams();
      setLLMParams(params);
      logger.info('LLM 参数加载成功', params);
    } catch (err) {
      logger.error('加载 LLM 参数失败', err);
    }
  }, []);

  const updateLLMParam = useCallback(async (key: keyof LLMParams, value: number | boolean) => {
    logger.info(`更新 LLM 参数: ${key} = ${value}`);
    try {
      const result = await api.setLLMParams({ [key]: value });
      setLLMParams(result.params);
      logger.info('LLM 参数更新成功');
    } catch (err) {
      logger.error('更新 LLM 参数失败', err);
    }
  }, []);

  const toggleShowThinking = useCallback(() => {
    setShowThinking(prev => {
      const newValue = !prev;
      localStorage.setItem('showThinking', String(newValue));
      logger.info(`思考过程显示: ${newValue}`);
      return newValue;
    });
  }, []);

  const loadLastRequest = useCallback(async () => {
    logger.debug('加载最后一次请求...');
    try {
      const data = await api.getLastRequest();
      if (data.success) {
        setLastRequest(data.request);
        logger.info('最后一次请求加载成功');
      } else {
        setLastRequest(null);
        logger.warn('无最后一次请求数据');
      }
    } catch (err) {
      logger.error('加载最后一次请求失败', err);
      setLastRequest(null);
    }
  }, []);

  const toggleRequestViewer = useCallback(() => {
    setShowRequestViewer(prev => {
      const newValue = !prev;
      if (newValue) {
        logger.info('打开请求查看器');
        loadLastRequest();
      } else {
        logger.info('关闭请求查看器');
      }
      return newValue;
    });
  }, [loadLastRequest]);

  const closeRequestViewer = useCallback(() => {
    logger.debug('关闭请求查看器');
    setShowRequestViewer(false);
  }, []);

  // ==================== 模型配置相关方法 ====================

  const loadModelConfigs = useCallback(async () => {
    logger.info('加载模型配置...');
    setModelConfigs(prev => ({ ...prev, isLoading: true }));
    try {
      const [llmData, embeddingData, rerankData] = await Promise.all([
        api.getModels('llm'),
        api.getModels('embedding'),
        api.getModels('rerank'),
      ]);
      
      setModelConfigs({
        llmModels: llmData.models,
        embeddingModels: embeddingData.models,
        rerankModels: rerankData.models,
        currentLLMModelId: llmData.current_model_id,
        currentEmbeddingModelId: embeddingData.current_model_id,
        currentRerankModelId: rerankData.current_model_id,
        isLoading: false,
      });
      logger.info('模型配置加载成功', {
        llm: llmData.models.length,
        embedding: embeddingData.models.length,
        rerank: rerankData.models.length,
      });
    } catch (err) {
      logger.error('加载模型配置失败', err);
      setModelConfigs(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  const addModelConfig = useCallback(async (
    modelType: ModelType,
    config: { name: string; model: string; api_key: string; base_url: string; is_default?: boolean }
  ): Promise<ModelConfig | null> => {
    logger.info(`添加 ${modelType} 模型配置: ${config.name}`);
    try {
      const result = await api.addModel(modelType, config);
      await loadModelConfigs(); // 重新加载以更新列表
      logger.info('模型配置添加成功', { id: result.id });
      return result;
    } catch (err) {
      logger.error(`添加 ${modelType} 模型配置失败`, err);
      return null;
    }
  }, [loadModelConfigs]);

  const updateModelConfig = useCallback(async (
    modelType: ModelType,
    modelId: string,
    config: Partial<{ name: string; model: string; api_key: string; base_url: string; is_default?: boolean }>
  ): Promise<ModelConfig | null> => {
    logger.info(`更新 ${modelType} 模型配置: ${modelId}`);
    try {
      const result = await api.updateModel(modelType, modelId, config);
      await loadModelConfigs(); // 重新加载以更新列表
      logger.info('模型配置更新成功');
      return result;
    } catch (err) {
      logger.error(`更新 ${modelType} 模型配置失败`, err);
      return null;
    }
  }, [loadModelConfigs]);

  const deleteModelConfig = useCallback(async (modelType: ModelType, modelId: string): Promise<boolean> => {
    logger.info(`删除 ${modelType} 模型配置: ${modelId}`);
    try {
      await api.deleteModel(modelType, modelId);
      await loadModelConfigs(); // 重新加载以更新列表
      logger.info('模型配置删除成功');
      return true;
    } catch (err) {
      logger.error(`删除 ${modelType} 模型配置失败`, err);
      return false;
    }
  }, [loadModelConfigs]);

  const setCurrentModel = useCallback(async (modelType: ModelType, modelId: string): Promise<boolean> => {
    logger.info(`切换 ${modelType} 当前模型: ${modelId}`);
    try {
      await api.setCurrentModel(modelType, modelId);
      await loadModelConfigs(); // 重新加载以更新列表
      logger.info('当前模型切换成功');
      return true;
    } catch (err) {
      logger.error(`切换 ${modelType} 当前模型失败`, err);
      return false;
    }
  }, [loadModelConfigs]);

  const setDefaultModel = useCallback(async (modelType: ModelType, modelId: string): Promise<boolean> => {
    logger.info(`设置 ${modelType} 默认模型: ${modelId}`);
    try {
      await api.setDefaultModel(modelType, modelId);
      await loadModelConfigs(); // 重新加载以更新列表
      logger.info('默认模型设置成功');
      return true;
    } catch (err) {
      logger.error(`设置 ${modelType} 默认模型失败`, err);
      return false;
    }
  }, [loadModelConfigs]);

  const testModelConnection = useCallback(async (
    modelType: ModelType,
    config: { model: string; api_key: string; base_url: string }
  ): Promise<{ success: boolean; message: string }> => {
    logger.info(`测试 ${modelType} 模型连接: ${config.model}`);
    try {
      const result = await api.testModelConnection(modelType, config);
      logger.info('模型连接测试结果', { success: result.success });
      return result;
    } catch (err: any) {
      logger.error(`测试 ${modelType} 模型连接失败`, err);
      // 提取 HTTP 状态码
      const status = err.status;
      let message = err.message || '连接测试失败';
      
      if (status === 400) {
        message = '请求参数错误 (400)';
      } else if (status === 401 || status === 403) {
        message = 'API Key 无效或权限不足 (401/403)';
      } else if (status === 404) {
        message = '模型不存在或接口不存在 (404)';
      } else if (status === 429) {
        message = '请求过于频繁，请稍后再试 (429)';
      } else if (status >= 500) {
        message = `服务器错误 (${status})`;
      }
      
      return { success: false, message };
    }
  }, []);

  // 初始化加载
  useEffect(() => {
    logger.info('应用初始化...');
    loadSessions();
    api.getRagMode()
      .then(mode => {
        setRagMode(mode);
        logger.info(`RAG 模式状态: ${mode}`);
      })
      .catch(err => logger.error('获取 RAG 模式失败', err));
    loadLLMParams();
    loadModelConfigs();
  }, [loadSessions, loadLLMParams, loadModelConfigs]);

  const value: AppState = {
    sessions,
    currentSessionId,
    messages,
    isStreaming,
    sidebarWidth,
    inspectorWidth,
    inspectorTab,
    inspectorFilePath,
    ragMode,
    llmParams,
    showThinking,
    lastRequest,
    showRequestViewer,
    theme,
    isDark,
    compressPreview,
    modelConfigs,
    loadSessions,
    createSession,
    selectSession,
    renameSession,
    deleteSession,
    sendMessage,
    stopStreaming,
    openCompressPreview,
    closeCompressPreview,
    executeCompress,
    compressSession,
    toggleRagMode,
    setInspectorTab,
    setInspectorFilePath,
    setSidebarWidth,
    setInspectorWidth,
    updateLLMParam,
    loadLLMParams,
    toggleShowThinking,
    loadLastRequest,
    toggleRequestViewer,
    closeRequestViewer,
    setTheme,
    loadModelConfigs,
    addModelConfig,
    updateModelConfig,
    deleteModelConfig,
    setCurrentModel,
    setDefaultModel,
    testModelConnection,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    const error = new Error('useApp must be used within AppProvider');
    logger.error('useApp 上下文错误', error);
    throw error;
  }
  return context;
}
