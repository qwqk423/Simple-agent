"use client";

import { useApp } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";
import { 
  AlertTriangle, 
  CheckCircle, 
  Loader2, 
  MessageSquare, 
  Sparkles,
  X
} from "lucide-react";
import { useEffect, useState } from "react";

export function CompressPreviewDialog() {
  const { 
    compressPreview, 
    closeCompressPreview, 
    executeCompress,
    currentSessionId 
  } = useApp();

  const [parsedRequest, setParsedRequest] = useState<any>(null);

  // 解析请求详情 JSON
  useEffect(() => {
    if (compressPreview.previewData?.request_detail) {
      try {
        const parsed = JSON.parse(compressPreview.previewData.request_detail);
        setParsedRequest(parsed);
      } catch (e) {
        console.error('Failed to parse request detail:', e);
        setParsedRequest(null);
      }
    }
  }, [compressPreview.previewData?.request_detail]);

  // 处理确认压缩
  const handleConfirm = async () => {
    await executeCompress();
  };

  // 格式化 JSON 显示
  const formatJSON = (obj: any) => JSON.stringify(obj, null, 2);

  return (
    <Dialog open={compressPreview.isOpen} onOpenChange={(open) => {
      if (!open && !compressPreview.isLoading) {
        closeCompressPreview();
      }
    }}>
      <DialogContent className="max-w-4xl w-[90vw] max-h-[90vh] p-0 gap-0 overflow-hidden">
        {/* 头部 */}
        <DialogHeader className="px-6 py-4 border-b border-border/50 bg-gradient-to-r from-blue-50/50 to-white dark:from-slate-800/30 dark:to-slate-900/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 to-blue-500 flex items-center justify-center shadow-md shadow-blue-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <DialogTitle className="text-lg font-semibold">对话压缩确认</DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground">
                查看即将发送到云端 API 的请求详情，确认后执行压缩
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* 内容区域 */}
        <div className="flex flex-col md:flex-row h-[60vh]">
          {/* 左侧：统计信息 */}
          <div className="w-full md:w-64 border-r border-border/50 bg-muted/20 p-4 space-y-4">
            <div className="space-y-3">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                压缩统计
              </h4>
              
              {compressPreview.isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              ) : compressPreview.error ? (
                <div className="flex items-center gap-2 text-red-500 text-sm">
                  <AlertTriangle className="w-4 h-4" />
                  <span>{compressPreview.error}</span>
                </div>
              ) : compressPreview.previewData ? (
                <div className="space-y-3">
                  <div className="bg-card rounded-xl p-3 border border-border/50">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <MessageSquare className="w-4 h-4" />
                      <span className="text-xs">新增消息</span>
                    </div>
                    <div className="text-2xl font-semibold text-foreground">
                      {compressPreview.previewData.new_messages_count}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      总消息: {compressPreview.previewData.total_messages_count}
                    </div>
                  </div>

                  {!compressPreview.previewData.can_compress && (
                    <div className="flex items-center gap-2 text-amber-600 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-sm">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                      <span>没有新消息需要压缩</span>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* 说明 */}
            <div className="pt-4 border-t border-border/50">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                压缩说明
              </h4>
              <ul className="text-xs text-muted-foreground space-y-1.5">
                <li className="flex items-start gap-1.5">
                  <span className="text-primary">•</span>
                  <span>仅压缩新增消息，已压缩内容不会重复处理</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-primary">•</span>
                  <span>每压缩3轮会自动合并摘要，保持上下文精简</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-primary">•</span>
                  <span>原始对话完整保留，可随时查看完整历史</span>
                </li>
              </ul>
            </div>
          </div>

          {/* 右侧：请求详情 */}
          <div className="flex-1 flex flex-col min-w-0">
            <div className="px-4 py-3 border-b border-border/50 bg-muted/10">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                云端 API 请求详情
              </h4>
            </div>
            
            <ScrollArea className="flex-1">
              <div className="p-4">
                {compressPreview.isLoading ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Loader2 className="w-8 h-8 animate-spin mb-3" />
                    <span className="text-sm">正在准备压缩预览...</span>
                  </div>
                ) : compressPreview.error ? (
                  <div className="flex flex-col items-center justify-center py-12 text-red-500">
                    <AlertTriangle className="w-8 h-8 mb-3" />
                    <span className="text-sm">{compressPreview.error}</span>
                  </div>
                ) : parsedRequest ? (
                  <div className="space-y-4">
                    {/* 模型信息 */}
                    <div className="bg-muted/30 rounded-lg p-3">
                      <span className="text-xs text-muted-foreground">模型</span>
                      <div className="text-sm font-medium mt-0.5">{parsedRequest.model}</div>
                    </div>

                    {/* 参数信息 */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-muted/30 rounded-lg p-3">
                        <span className="text-xs text-muted-foreground">Temperature</span>
                        <div className="text-sm font-medium mt-0.5">{parsedRequest.temperature}</div>
                      </div>
                      <div className="bg-muted/30 rounded-lg p-3">
                        <span className="text-xs text-muted-foreground">Max Tokens</span>
                        <div className="text-sm font-medium mt-0.5">{parsedRequest.max_tokens}</div>
                      </div>
                    </div>

                    {/* 消息内容 */}
                    <div>
                      <span className="text-xs text-muted-foreground mb-2 block">消息内容</span>
                      <pre className="whitespace-pre-wrap break-all text-sm text-muted-foreground bg-muted/50 p-4 rounded-xl border border-border/30 font-mono text-xs leading-relaxed max-h-[300px] overflow-auto">
                        {formatJSON(parsedRequest.messages)}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <MessageSquare className="w-8 h-8 mb-3 opacity-50" />
                    <span className="text-sm">暂无请求详情</span>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* 底部按钮 */}
        <DialogFooter className="px-6 py-4 border-t border-border/50 bg-muted/20 gap-2">
          <Button
            variant="outline"
            onClick={closeCompressPreview}
            disabled={compressPreview.isLoading}
            className="rounded-lg"
          >
            <X className="w-4 h-4 mr-2" />
            取消
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={compressPreview.isLoading || !compressPreview.previewData?.can_compress}
            className="rounded-lg bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white shadow-md shadow-blue-500/20"
          >
            {compressPreview.isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                压缩中...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                确认压缩
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
