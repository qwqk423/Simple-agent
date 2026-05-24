"use client";

import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Square, MessageCircle, FileText, Zap, Sparkles, ChevronDown } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { useApp } from "@/lib/store";
import { getLogger } from "@/lib/logger";

const logger = getLogger('ChatPanel');

export function ChatPanel() {
  const { messages, sendMessage, stopStreaming, compressSession, isStreaming, currentSessionId, showThinking } = useApp();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);

  logger.debug('ChatPanel 渲染', { 
    messageCount: messages.length, 
    isStreaming, 
    currentSessionId,
    isNearBottom 
  });

  // 检查是否在底部附近（阈值 100px）
  const checkIsNearBottom = () => {
    const scrollContainer = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (!scrollContainer) return true;
    
    try {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainer as HTMLElement;
      const distanceToBottom = scrollHeight - scrollTop - clientHeight;
      return distanceToBottom < 100;
    } catch (err) {
      logger.error('检查滚动位置失败', err);
      return true;
    }
  };

  // 滚动到底部
  const scrollToBottom = () => {
    logger.debug('用户手动滚动到底部');
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // 监听滚动事件
  useEffect(() => {
    const scrollContainer = scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (!scrollContainer) {
      logger.warn('找不到滚动容器');
      return;
    }

    const handleScroll = () => {
      try {
        const nearBottom = checkIsNearBottom();
        setIsNearBottom(nearBottom);
        setShowScrollButton(!nearBottom && messages.length > 0);
      } catch (err) {
        logger.error('滚动事件处理失败', err);
      }
    };

    scrollContainer.addEventListener('scroll', handleScroll);
    return () => scrollContainer.removeEventListener('scroll', handleScroll);
  }, [messages.length]);

  // 消息更新时，只有在底部附近才自动滚动
  useEffect(() => {
    if (bottomRef.current && isNearBottom) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isNearBottom]);

  const handleCommand = (command: string) => {
    logger.info(`执行命令: ${command}`);
    switch (command) {
      case 'compact':
        compressSession();
        break;
      default:
        sendMessage('/' + command);
    }
  };

  const handleSendMessage = async (content: string, images?: string[]) => {
    logger.logUserAction('发送消息', { contentLength: content.length, hasImages: !!images?.length });
    try {
      await sendMessage(content, images);
    } catch (err) {
      logger.error('发送消息失败', err);
    }
  };

  const handleStopStreaming = () => {
    logger.logUserAction('中断流式响应');
    stopStreaming();
  };

  if (!currentSessionId) {
    return (
      <div className="h-full flex flex-col relative overflow-hidden">
        {/* 欢迎界面 - 输入框单独垂直居中，标题和标签在输入框上方 */}
        <div className="flex-1 flex flex-col">
          {/* 标题和标签 - 放在输入框上方 */}
          <div className="flex-1 flex flex-col items-center justify-end pb-8">
            <div className="text-center space-y-6 px-4">
              {/* 装饰图标 */}
              <div className="relative mx-auto w-fit animate-fade-in-scale">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-xl shadow-blue-500/20">
                  <Sparkles className="w-10 h-10 text-white" />
                </div>
              </div>

              <div className="space-y-3 animate-fade-in-up stagger-1">
                <h2 className="font-serif text-3xl font-semibold text-foreground">
                  Simple Agent
                </h2>
              </div>

              {/* 特性标签 */}
              <div className="flex flex-wrap gap-2 justify-center animate-fade-in-up stagger-2">
                {[
                  { icon: FileText, text: "文件即记忆" },
                  { icon: Zap, text: "技能即插件" },
                  { icon: MessageCircle, text: "全透明" },
                ].map(({ icon: Icon, text }, i) => (
                  <span
                    key={text}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-muted/70 rounded-full text-sm text-muted-foreground hover:bg-muted transition-colors cursor-default"
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {text}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* 输入框区域 - 垂直居中 */}
          <div className="w-full max-w-3xl mx-auto px-4">
            <ChatInput onSend={handleSendMessage} disabled={isStreaming} expanded />
          </div>

          {/* 占位空间，平衡输入框上方的空间 */}
          <div className="flex-1" />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col relative">
      {/* 消息列表 */}
      <ScrollArea className="flex-1" ref={scrollRef}>
        <div className="min-h-full py-4">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center p-8">
              <div className="text-center space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mx-auto">
                  <MessageCircle className="w-6 h-6 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-sm">发送消息开始对话...</p>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div 
                key={message.id}
                style={{ animationDelay: `${Math.min(index * 0.05, 0.5)}s` }}
              >
                <ChatMessage message={message} showThinking={showThinking} />
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* 滚动到底部按钮 */}
      {showScrollButton && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-24 left-1/2 -translate-x-1/2 z-10
                     flex items-center gap-1.5 px-3 py-1.5
                     bg-primary text-primary-foreground
                     rounded-full shadow-lg hover:bg-primary/90
                     transition-all duration-200 animate-fade-in-up"
        >
          <ChevronDown className="w-4 h-4" />
          <span className="text-xs font-medium">回到底部</span>
        </button>
      )}

      {/* 中断按钮 / 输入框 */}
      {isStreaming ? (
        <div className="border-t border-border/50 bg-card/50 backdrop-blur-sm p-4 animate-fade-in-up">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-center">
              <Button
                onClick={handleStopStreaming}
                variant="outline"
                className="gap-2 rounded-xl border-red-200 bg-red-50 text-red-700 hover:bg-red-100 hover:text-red-800 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300 dark:hover:bg-red-950/30 transition-all duration-300"
              >
                <Square className="w-4 h-4 fill-current" />
                中断回复
              </Button>
            </div>
            <div className="mt-2 text-xs text-center text-muted-foreground/70">
              中断后不会保存本次对话内容
            </div>
          </div>
        </div>
      ) : (
        <ChatInput onSend={handleSendMessage} onCommand={handleCommand} disabled={isStreaming} />
      )}
    </div>
  );
}
