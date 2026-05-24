"use client";

import { useState, useRef, useEffect } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { InspectorPanel } from "@/components/editor/InspectorPanel";
import { FloatingOrbs } from "@/components/layout/FloatingOrbs";
import { CompressPreviewDialog } from "@/components/compress/CompressPreviewDialog";
import { PanelLeft, PanelRight } from "lucide-react";

export default function Home() {
  const [sidebarWidth, setSidebarWidth] = useState(200);
  const [inspectorWidth, setInspectorWidth] = useState(430);
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);
  const [isResizingInspector, setIsResizingInspector] = useState(false);
  const [isSidebarGhost, setIsSidebarGhost] = useState(false);
  const [isInspectorGhost, setIsInspectorGhost] = useState(false);
  
  // 侧边栏收起状态
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [isInspectorCollapsed, setIsInspectorCollapsed] = useState(true);
  
  const containerRef = useRef<HTMLDivElement>(null);

  // 处理侧边栏拖拽
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingSidebar && !isSidebarCollapsed) {
        const newWidth = Math.max(200, Math.min(400, e.clientX));
        setSidebarWidth(newWidth);
      }
      if (isResizingInspector && !isInspectorCollapsed) {
        const containerWidth = containerRef.current?.clientWidth || window.innerWidth;
        const newWidth = Math.max(320, Math.min(500, containerWidth - e.clientX));
        setInspectorWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizingSidebar(false);
      setIsResizingInspector(false);
      setIsSidebarGhost(false);
      setIsInspectorGhost(false);
    };

    if (isResizingSidebar || isResizingInspector) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizingSidebar, isResizingInspector, isSidebarCollapsed, isInspectorCollapsed]);

  return (
    <div ref={containerRef} className="h-screen flex flex-col bg-background relative overflow-hidden">
      {/* 背景光斑 */}
      <FloatingOrbs />
      
      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden relative z-10">
        {/* 左侧边栏 */}
        {!isSidebarCollapsed ? (
          <>
            <div 
              className={`
                flex-shrink-0 transition-all duration-200 ease-out
                ${isSidebarGhost ? 'opacity-90 scale-[1.01]' : ''}
              `}
              style={{ width: sidebarWidth }}
            >
              <Sidebar onCollapse={() => setIsSidebarCollapsed(true)} />
            </div>
            
            {/* 拖拽条 - 左侧 */}
            <div
              className={`
                w-1.5 cursor-col-resize transition-all duration-200 relative z-20
                ${isResizingSidebar 
                  ? 'bg-primary/40 w-1.5' 
                  : 'bg-border/30 hover:bg-primary/30'
                }
              `}
              onMouseDown={() => {
                setIsResizingSidebar(true);
                setIsSidebarGhost(true);
              }}
            >
              {/* 拖拽指示器 */}
              <div className={`
                absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                w-1 h-8 rounded-full transition-all duration-200
                ${isResizingSidebar ? 'bg-primary' : 'bg-transparent'}
              `} />
            </div>
          </>
        ) : (
          /* 左侧栏展开按钮 */
          <div className="flex-shrink-0 w-12 flex flex-col items-center pt-4 border-r border-border/30 bg-muted/20">
            <button
              onClick={() => setIsSidebarCollapsed(false)}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200"
              title="展开左侧栏"
            >
              <PanelLeft className="w-4 h-4" />
            </button>
          </div>
        )}
        
        {/* 中间聊天区域 */}
        <div className="flex-1 min-w-0 bg-background/30 backdrop-blur-[1px]">
          <ChatPanel />
        </div>
        
        {/* 右侧检查器 */}
        {!isInspectorCollapsed ? (
          <>
            {/* 拖拽条 - 右侧 */}
            <div
              className={`
                w-1.5 cursor-col-resize transition-all duration-200 relative z-20
                ${isResizingInspector 
                  ? 'bg-primary/40 w-1.5' 
                  : 'bg-border/30 hover:bg-primary/30'
                }
              `}
              onMouseDown={() => {
                setIsResizingInspector(true);
                setIsInspectorGhost(true);
              }}
            >
              {/* 拖拽指示器 */}
              <div className={`
                absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                w-1 h-8 rounded-full transition-all duration-200
                ${isResizingInspector ? 'bg-primary' : 'bg-transparent'}
              `} />
            </div>
            
            <div 
              className={`
                flex-shrink-0 transition-all duration-200 ease-out
                ${isInspectorGhost ? 'opacity-90 scale-[1.01]' : ''}
              `}
              style={{ width: inspectorWidth }}
            >
              <InspectorPanel onCollapse={() => setIsInspectorCollapsed(true)} />
            </div>
          </>
        ) : (
          /* 右侧栏展开按钮 */
          <div className="flex-shrink-0 w-12 flex flex-col items-center pt-4 border-l border-border/30 bg-muted/20">
            <button
              onClick={() => setIsInspectorCollapsed(false)}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200"
              title="展开右侧栏"
            >
              <PanelRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
      
      {/* 拖拽时的遮罩层 */}
      {(isResizingSidebar || isResizingInspector) && (
        <div className="fixed inset-0 z-50 pointer-events-none" />
      )}
      
      {/* 压缩预览弹窗 */}
      <CompressPreviewDialog />
    </div>
  );
}
