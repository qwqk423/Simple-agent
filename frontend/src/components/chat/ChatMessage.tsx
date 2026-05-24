"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  ChevronDown, 
  ChevronRight, 
  Terminal, 
  Globe, 
  FileCode, 
  Search, 
  CheckCircle, 
  XCircle, 
  Loader2,
  User,
  Bot,
} from "lucide-react";
import { Message } from "@/lib/store";
import { ToolCall } from "@/lib/api";
import { TodoList } from "./TodoList";

interface ChatMessageProps {
  message: Message;
  showThinking?: boolean;
}

function ToolIcon({ tool, status }: { tool?: string; status?: string }) {
  const className = "w-4 h-4";
  const colorClass = status === 'running' ? 'text-amber-500' : 
                     status === 'error' ? 'text-red-500' : 
                     status === 'success' ? 'text-emerald-500' : 'text-nature-sage';
  
  // 如果 tool 未定义，返回默认图标
  if (!tool) {
    return <Terminal className={`${className} ${colorClass}`} />;
  }
  
  if (tool.includes("terminal") || tool.includes("shell")) 
    return <Terminal className={`${className} ${colorClass}`} />;
  if (tool.includes("python") || tool.includes("repl")) 
    return <FileCode className={`${className} ${colorClass}`} />;
  if (tool.includes("fetch") || tool.includes("url")) 
    return <Globe className={`${className} ${colorClass}`} />;
  if (tool.includes("search") || tool.includes("knowledge")) 
    return <Search className={`${className} ${colorClass}`} />;
  return <Terminal className={`${className} ${colorClass}`} />;
}

function formatDuration(ms?: number): string {
  if (!ms) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function ThoughtChain({ toolCalls }: { toolCalls: ToolCall[] }) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [outputExpanded, setOutputExpanded] = useState<Record<number, boolean>>({});

  const toggleExpand = (index: number) => {
    setExpanded(prev => ({ ...prev, [index]: !prev[index] }));
  };
  
  const toggleOutputExpand = (index: number) => {
    setOutputExpanded(prev => ({ ...prev, [index]: !prev[index] }));
  };

  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="mt-2 space-y-1">
      {toolCalls.map((call, index) => {
        const isRunning = call.status === 'running' || (!call.status && !call.output);
        const isSuccess = call.status === 'success' || (call.output !== undefined && call.output !== '');
        const isError = call.status === 'error';
        const hasOutput = (isSuccess || isError) && call.output;
        
        return (
          <div key={call.id || index}>
            <button
              onClick={() => toggleExpand(index)}
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {expanded[index] ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
              <ToolIcon tool={call.tool} status={call.status} />
              <span>{call.tool || '未知工具'}</span>
              {isRunning ? (
                <Loader2 className="w-3 h-3 animate-spin text-amber-500" />
              ) : isError ? (
                <XCircle className="w-3 h-3 text-red-500" />
              ) : (
                <CheckCircle className="w-3 h-3 text-emerald-500" />
              )}
              {call.duration && <span className="text-muted-foreground/60">{formatDuration(call.duration)}</span>}
            </button>
            
            {expanded[index] && (
              <div className="ml-5 mt-1.5 space-y-1.5 text-xs">
                <div className="text-muted-foreground">
                  <span className="font-medium">输入: </span>
                  <span className="font-mono">{typeof call.input === 'string' ? call.input : JSON.stringify(call.input)}</span>
                </div>
                
                {hasOutput && (
                  <div>
                    <button
                      onClick={() => toggleOutputExpand(index)}
                      className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {outputExpanded[index] ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      <span className="font-medium">{isError ? '错误信息' : '执行结果'}</span>
                    </button>
                    {outputExpanded[index] && (
                      <pre className={`mt-1 whitespace-pre-wrap font-mono ${isError ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'}`}>
                        {call.output!.length > 2000 ? call.output!.slice(0, 2000) + '\n...' : call.output}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function RetrievalCard({ retrievals }: { retrievals: any[] }) {
  const [expanded, setExpanded] = useState(false);

  if (!retrievals || retrievals.length === 0) return null;

  return (
    <div className="mt-3 bg-blue-50/70 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-800/50 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 hover:bg-blue-100/50 dark:hover:bg-blue-900/20 transition-colors"
      >
        <Search className="w-4 h-4 text-blue-500 dark:text-blue-400" />
        <span className="text-sm font-medium text-blue-600 dark:text-blue-300">
          记忆检索 ({retrievals.length} 条结果)
        </span>
        {expanded ? (
          <ChevronDown className="w-4 h-4 ml-auto text-nature-stone dark:text-nature-sage" />
        ) : (
          <ChevronRight className="w-4 h-4 ml-auto text-nature-stone dark:text-nature-sage" />
        )}
      </button>
      
      {expanded && (
        <div className="px-3.5 pb-3.5 space-y-2">
          {retrievals.map((r, i) => (
            <div key={i} className="bg-white dark:bg-slate-800 rounded-lg p-2.5 text-xs border border-blue-100/50 dark:border-blue-800/30">
              <div className="flex items-center gap-3 text-blue-600 dark:text-blue-300 mb-1.5">
                <span className="font-medium">{r.source}</span>
                <span className="text-slate-400">{(r.score * 100).toFixed(0)}% 相关</span>
              </div>
              <p className="text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed">{r.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ThinkingBlock({ thinking, showThinking }: { thinking?: string; showThinking: boolean }) {
  const [expanded, setExpanded] = useState(false);
  
  if (!showThinking) return null;
  
  const hasThinking = thinking && thinking.trim().length > 0;
  
  return (
    <div className="my-3 bg-muted/50 dark:bg-muted/30 rounded-xl border border-border/50 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 hover:bg-muted/70 dark:hover:bg-muted/50 transition-colors text-left"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        )}
        <span className="text-sm font-medium text-muted-foreground">思考过程</span>
        <span className="text-xs text-muted-foreground/60 ml-auto">
          {expanded ? '收起' : '展开'}
        </span>
      </button>
      
      {expanded && (
        <div className="px-3.5 pb-3.5">
          {hasThinking ? (
            <div className="bg-card rounded-lg p-3 text-sm text-muted-foreground whitespace-pre-wrap border border-border/30">
              {thinking}
            </div>
          ) : (
            <div className="bg-muted/50 rounded-lg p-3 text-sm text-muted-foreground/60 italic">
              未开启思考模式或此模型不支持
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ChatMessage({ message, showThinking = true }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) return null;

  return (
    <div className="py-4 animate-fade-in-up">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <div className={`flex items-start gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
          {/* 头像 */}
          <div className={`
            w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0
            shadow-sm transition-all duration-300
            ${isUser 
              ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white' 
              : 'bg-gradient-to-br from-sky-400 to-blue-400 text-white'
            }
          `}>
            {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
          </div>
          
          {/* 消息区域 */}
          <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[80%]`}>
            {/* 角色名 */}
            <div className="text-xs font-medium text-muted-foreground mb-1.5 px-1">
              {isUser ? '你' : 'Simple Agent'}
            </div>
            
            {/* 思考过程 */}
            {!isUser && (
              <ThinkingBlock thinking={message.thinking} showThinking={showThinking} />
            )}
            
            {/* 图片显示 */}
            {message.images && message.images.length > 0 && (
              <div className={`flex flex-wrap gap-2 mb-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
                {message.images.map((img, index) => (
                  <div
                    key={index}
                    className="relative rounded-xl overflow-hidden border border-border/50 shadow-sm max-w-[200px] max-h-[200px]"
                  >
                    <img
                      src={img}
                      alt={`图片 ${index + 1}`}
                      className="w-full h-full object-cover cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => window.open(img, '_blank')}
                    />
                  </div>
                ))}
              </div>
            )}

            {/* 消息气泡 */}
            <div
              className={`
                message-bubble
                ${isUser ? 'message-bubble-user' : 'message-bubble-ai'}
              `}
            >
              {message.content ? (
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => <p className="m-0 leading-relaxed">{children}</p>,
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : message.toolCalls && message.toolCalls.length > 0 ? (
                // 有工具调用但没有内容时，显示工具调用提示
                <div className="text-sm text-muted-foreground py-1">
                  正在使用工具...
                </div>
              ) : (
                <div className="flex items-center gap-2 text-muted-foreground py-1">
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  <span className="text-sm ml-1">思考中...</span>
                </div>
              )}
            </div>
            
            {/* 检索结果 */}
            {message.retrievals && message.retrievals.length > 0 && (
              <div className="w-full mt-2">
                <RetrievalCard retrievals={message.retrievals} />
              </div>
            )}
            
            {/* 工具调用链 */}
            {message.toolCalls && message.toolCalls.length > 0 && (
              <div className="w-full mt-2">
                <ThoughtChain toolCalls={message.toolCalls} />
              </div>
            )}
            
            {/* 待办事项列表 */}
            {Array.isArray(message.todos) && message.todos.length > 0 && (
              <div className="w-full mt-2">
                <TodoList 
                  todos={message.todos} 
                  completedCount={message.todos.filter((t: any) => t.status === 'completed').length}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
