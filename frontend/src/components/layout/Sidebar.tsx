"use client";

import { useState, useRef } from "react";
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Edit2, 
  Check, 
  X,
  Eye,
  RefreshCw,
  Sparkles,
  PanelLeft,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { useApp } from "@/lib/store";
import { formatDate } from "@/lib/utils";

interface SidebarProps {
  onCollapse?: () => void;
}

export function Sidebar({ onCollapse }: SidebarProps) {
  const {
    sessions,
    currentSessionId,
    createSession,
    selectSession,
    renameSession,
    deleteSession,
    lastRequest,
    showRequestViewer,
    loadLastRequest,
    toggleRequestViewer,
    closeRequestViewer,
  } = useApp();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [panelHeight, setPanelHeight] = useState(60);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartY = useRef(0);
  const dragStartHeight = useRef(60);

  const handleRename = (sessionId: string, currentTitle: string) => {
    setEditingId(sessionId);
    setEditTitle(currentTitle);
  };

  const handleSaveRename = async (sessionId: string) => {
    if (editTitle.trim()) {
      await renameSession(sessionId, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = () => {
    setEditingId(null);
    setEditTitle("");
  };

  const handleDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = panelHeight;
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      moveEvent.preventDefault();
      const container = document.querySelector('.sidebar-container') as HTMLElement;
      if (!container) return;
      
      const containerHeight = container.clientHeight;
      const deltaY = startY - moveEvent.clientY;
      const deltaPercent = (deltaY / containerHeight) * 100;
      const newHeight = Math.min(Math.max(startHeight + deltaPercent, 20), 85);
      
      requestAnimationFrame(() => {
        setPanelHeight(newHeight);
      });
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      setIsDragging(false);
    };

    setIsDragging(true);
    document.addEventListener('mousemove', handleMouseMove, { passive: false });
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  };

  // 截断 base64 图片数据（仅显示用途）
  const truncateBase64 = (value: string): string => {
    const base64Prefix = 'data:image/';
    if (value.startsWith(base64Prefix) && value.length > 50) {
      return value.substring(0, 50) + '... [base64 图片数据] ...';
    }
    return value;
  };

  const formatRequestContent = () => {
    if (!lastRequest) return "暂无请求记录";
    try {
      // 递归处理对象，截断 base64 图片
      const processValue = (value: any): any => {
        if (typeof value === 'string') {
          return truncateBase64(value);
        }
        if (Array.isArray(value)) {
          return value.map(processValue);
        }
        if (value && typeof value === 'object') {
          const result: any = {};
          for (const key in value) {
            result[key] = processValue(value[key]);
          }
          return result;
        }
        return value;
      };

      const processed = processValue(lastRequest);
      return JSON.stringify(processed, null, 2);
    } catch (e) {
      return String(lastRequest);
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-muted/20 border-r border-border/30 sidebar-container relative theme-transition">
      {/* 顶部标题栏和收起按钮 */}
      <div className="flex items-center justify-between p-4 border-b border-border/30">
        {/* Logo 和标题 */}
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            {/* 装饰光晕 */}
            <div className="absolute -inset-1 rounded-xl bg-blue-400/20 blur-md -z-10 animate-pulse-soft" />
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-base font-semibold tracking-tight text-foreground">
              Simple Agent
            </span>
            <span className="text-[9px] text-muted-foreground -mt-0.5">
              轻盈自然的 AI 对话
            </span>
          </div>
        </div>
        
        {/* 收起按钮 */}
        <button
          onClick={onCollapse}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200"
          title="收起左侧栏"
        >
          <PanelLeft className="w-4 h-4" />
        </button>
      </div>

      {/* 工具栏 */}
      <div className="p-4 space-y-3 animate-fade-in-up">
        {/* 新对话按钮 */}
        <Button 
          onClick={createSession}
          className="w-full justify-start gap-2.5 rounded-xl h-11 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white shadow-sm shadow-blue-500/25 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/30 hover:-translate-y-0.5"
        >
          <Plus className="w-4 h-4" />
          <span className="font-medium">新对话</span>
        </Button>
        
        {/* 查看请求按钮 */}
        <Button 
          onClick={toggleRequestViewer}
          variant="outline"
          className={`
            w-full justify-start gap-2.5 rounded-xl h-11 
            border-border/50 hover:border-primary/30 hover:bg-primary/5
            transition-all duration-300
            ${showRequestViewer ? 'bg-primary/5 border-primary/30 text-primary' : ''}
          `}
        >
          <Eye className="w-4 h-4" />
          <span className="font-medium">查看请求</span>
        </Button>
      </div>

      {/* 分隔线 */}
      <div className="mx-4 h-px bg-border/50" />

      {/* 会话列表 */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1">
          <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            会话历史
          </div>
          {sessions.map((session, index) => (
            <div
              key={session.id}
              className={`
                group flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer
                transition-all duration-300 ease-out
                animate-fade-in-up
                ${currentSessionId === session.id
                  ? 'bg-blue-50 border border-blue-200 shadow-sm dark:bg-blue-900/20 dark:border-blue-800'
                  : 'hover:bg-slate-50/70 border border-transparent dark:hover:bg-slate-800/50'
                }
              `}
              style={{ animationDelay: `${index * 0.05}s` }}
              onClick={() => selectSession(session.id)}
            >
              <div className={`
                w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                transition-all duration-300
                ${currentSessionId === session.id 
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400' 
                  : 'bg-slate-100 text-slate-500 group-hover:bg-white dark:bg-slate-800 dark:text-slate-400'
                }
              `}>
                <MessageSquare className="w-4 h-4" />
              </div>
              
              {editingId === session.id ? (
                <div className="flex-1 flex items-center gap-1.5">
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveRename(session.id);
                      if (e.key === 'Escape') handleCancelRename();
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="flex-1 text-sm px-2 py-1 border border-primary/30 rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                    autoFocus
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSaveRename(session.id);
                    }}
                    className="p-1.5 hover:bg-primary/10 rounded-lg text-primary transition-colors"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCancelRename();
                    }}
                    className="p-1.5 hover:bg-muted rounded-lg text-muted-foreground transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex-1 min-w-0">
                    <span className={`
                      block text-sm truncate font-medium
                      ${currentSessionId === session.id ? 'text-blue-600 dark:text-blue-400' : 'text-foreground'}
                    `}>
                      {session.title || '新对话'}
                    </span>
                    <span className="block text-[10px] text-muted-foreground">
                      {formatDate(session.updatedAt / 1000)}
                    </span>
                  </div>
                  
                  {/* 操作按钮 */}
                  <div className="hidden group-hover:flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all duration-200">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRename(session.id, session.title);
                      }}
                      className="p-1.5 hover:bg-muted rounded-lg text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(session.id);
                      }}
                      className="p-1.5 hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded-lg transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
          
          {sessions.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">暂无会话</p>
              <p className="text-xs mt-1">点击上方按钮开始</p>
            </div>
          )}
        </div>
      </ScrollArea>
      
      {/* 请求查看器浮窗 */}
      {showRequestViewer && (
        <div 
          className="absolute inset-x-0 bottom-0 bg-card rounded-t-3xl shadow-[0_-8px_32px_rgba(0,0,0,0.12)] z-50 animate-slide-in-right border-t border-border/50"
          style={{ height: `${panelHeight}%` }}
        >
          {/* 拖动指示条 */}
          <div 
            className={`
              absolute top-0 left-0 right-0 h-7 flex items-center justify-center cursor-ns-resize z-20
              transition-colors duration-200
              ${isDragging ? 'bg-primary/5' : 'hover:bg-muted/50'}
            `}
            onMouseDown={handleDragStart}
          >
            <div className={`
              w-12 h-1 rounded-full transition-all duration-200
              ${isDragging ? 'bg-primary w-16' : 'bg-muted-foreground/30'}
            `} />
          </div>
          
          {/* 头部 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-muted/20 rounded-t-3xl mt-5">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                <Eye className="w-4.5 h-4.5 text-primary" />
              </div>
              <div>
                <h3 className="font-medium text-sm">发送给 AI 的请求</h3>
                <p className="text-xs text-muted-foreground">
                  {lastRequest ? `模型: ${lastRequest.model || '未知'}` : '暂无记录'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={loadLastRequest}
                className="rounded-lg hover:bg-muted"
                title="刷新"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={closeRequestViewer}
                className="rounded-lg hover:bg-muted"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
          
          {/* 内容 */}
          <ScrollArea className="h-[calc(100%-70px-16px)]">
            <div className="p-4">
              {lastRequest ? (
                <pre className="whitespace-pre-wrap break-all text-sm text-muted-foreground bg-muted/50 p-4 rounded-xl border border-border/30 font-mono text-xs leading-relaxed">
                  {formatRequestContent()}
                </pre>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <Eye className="w-12 h-12 mb-4 opacity-20" />
                  <p className="text-sm">暂无请求记录</p>
                  <p className="text-xs mt-1 opacity-70">发送一条消息后可以看到完整请求</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
