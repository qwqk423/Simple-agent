"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Editor from "@monaco-editor/react";
import { 
  FileText, 
  Save, 
  RefreshCw, 
  FolderOpen,
  Settings,
  Brain,
  X,
  Wrench,
  Sparkles,
  Zap,
  Code2,
  Database,
  PanelRight,
  Sun,
  Moon,
  Monitor,
  ChevronDown,
  Server,
  Layers,
  GitBranch,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useApp } from "@/lib/store";
import * as api from "@/lib/api";
import { ModelConfig } from "@/lib/types";
import { ModelConfigPanel } from "./ModelConfigPanel";

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'dir';
  children?: FileNode[];
}

const DEFAULT_FILES: FileNode[] = [
  {
    name: "workspace",
    path: "workspace",
    type: "dir",
    children: [
      { name: "SOUL.md", path: "workspace/SOUL.md", type: "file" },
      { name: "IDENTITY.md", path: "workspace/IDENTITY.md", type: "file" },
      { name: "USER.md", path: "workspace/USER.md", type: "file" },
      { name: "AGENTS.md", path: "workspace/AGENTS.md", type: "file" },
      { name: "MEMORY.md", path: "workspace/MEMORY.md", type: "file" }
    ]
  }
];

// LLM 参数滑块组件
function ParamSlider({ 
  label, 
  value, 
  min, 
  max, 
  step, 
  onChange,
  disabled = false
}: { 
  label: string; 
  value: number; 
  min: number; 
  max: number; 
  step: number; 
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  const percentage = ((value - min) / (max - min)) * 100;
  
  return (
    <div className={`space-y-3 ${disabled ? 'opacity-50' : ''}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded-md text-foreground">{value}</span>
      </div>
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          disabled={disabled}
          className="w-full h-2 rounded-full appearance-none cursor-pointer bg-muted"
          style={{
            background: `linear-gradient(to right, hsl(var(--primary)) 0%, hsl(var(--primary)) ${percentage}%, hsl(var(--muted)) ${percentage}%, hsl(var(--muted)) 100%)`
          }}
        />
      </div>
    </div>
  );
}

// 模型选择下拉组件
function ModelSelect({
  models,
  currentId,
  onChange,
  label,
  icon: Icon,
}: {
  models: ModelConfig[];
  currentId: string | null;
  onChange: (modelId: string) => void;
  label: string;
  icon: React.ElementType;
}) {
  const currentModel = models.find(m => m.id === currentId) || models[0];
  
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </div>
      <div className="relative">
        <select
          value={currentId || ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 text-sm bg-muted/50 border border-border/50 rounded-lg appearance-none cursor-pointer hover:bg-muted transition-colors"
        >
          {models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name} {model.is_default ? '(默认)' : ''}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
      </div>
      {currentModel && (
        <div className="text-xs text-muted-foreground px-1 truncate">
          {currentModel.model}
        </div>
      )}
    </div>
  );
}

// 模型选择面板
function ModelPanel({ onOpenModelConfig }: { onOpenModelConfig: () => void }) {
  const {
    modelConfigs,
    setCurrentModel,
  } = useApp();

  return (
    <div className="p-5 space-y-6">
      <div className="flex items-center gap-3 pb-4 border-b border-border/50">
        <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center dark:bg-purple-900/20">
          <Server className="w-5 h-5 text-purple-500 dark:text-purple-400" />
        </div>
        <div>
          <h3 className="font-medium text-foreground">模型选择</h3>
          <p className="text-xs text-muted-foreground">切换当前使用的模型</p>
        </div>
      </div>

      <div className="space-y-5">
        <ModelSelect
          models={modelConfigs.llmModels}
          currentId={modelConfigs.currentLLMModelId}
          onChange={(id) => setCurrentModel('llm', id)}
          label="LLM 模型"
          icon={Brain}
        />

        <ModelSelect
          models={modelConfigs.embeddingModels}
          currentId={modelConfigs.currentEmbeddingModelId}
          onChange={(id) => setCurrentModel('embedding', id)}
          label="Embedding 模型"
          icon={Layers}
        />

        <ModelSelect
          models={modelConfigs.rerankModels}
          currentId={modelConfigs.currentRerankModelId}
          onChange={(id) => setCurrentModel('rerank', id)}
          label="Rerank 模型"
          icon={GitBranch}
        />
      </div>

      {/* 管理模型按钮 */}
      <div className="pt-4 border-t border-border/50">
        <Button
          variant="outline"
          size="sm"
          onClick={onOpenModelConfig}
          className="w-full gap-1.5"
        >
          <Settings className="w-3.5 h-3.5" />
          管理模型
          <ExternalLink className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
}

// LLM 设置面板
function LLMSettingsPanel({ onOpenModelConfig }: { onOpenModelConfig: () => void }) {
  const { 
    llmParams, 
    updateLLMParam, 
    showThinking, 
    toggleShowThinking, 
    compressSession, 
    isStreaming, 
    currentSessionId, 
    ragMode, 
    toggleRagMode,
  } = useApp();

  return (
    <div className="p-5 space-y-6">
      <div className="flex items-center gap-3 pb-4 border-b border-border/50">
        <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center dark:bg-blue-900/20">
          <Brain className="w-5 h-5 text-blue-500 dark:text-blue-400" />
        </div>
        <div>
          <h3 className="font-medium text-foreground">模型参数</h3>
          <p className="text-xs text-muted-foreground">调整 LLM 生成参数，实时生效</p>
        </div>
      </div>

      <div className="space-y-5">
        <ParamSlider
          label="Temperature (温度)"
          value={llmParams.temperature}
          min={0}
          max={2}
          step={0.1}
          onChange={(v) => updateLLMParam('temperature', v)}
        />

        <ParamSlider
          label="Top-P (核采样)"
          value={llmParams.top_p}
          min={0}
          max={1}
          step={0.05}
          onChange={(v) => updateLLMParam('top_p', v)}
        />

        <ParamSlider
          label="Presence Penalty (存在惩罚)"
          value={llmParams.presence_penalty}
          min={-2}
          max={2}
          step={0.1}
          onChange={(v) => updateLLMParam('presence_penalty', v)}
        />

        <ParamSlider
          label="Max Tokens (最大长度)"
          value={llmParams.max_tokens}
          min={256}
          max={8192}
          step={256}
          onChange={(v) => updateLLMParam('max_tokens', v)}
        />
      </div>

      {/* 开关设置 */}
      <div className="pt-5 border-t border-border/50 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium block">模型思考模式</span>
            <span className="text-xs text-muted-foreground">控制模型是否生成思考过程</span>
          </div>
          <button
            onClick={() => updateLLMParam('thinking_enabled', !llmParams.thinking_enabled)}
            className={`
              relative w-11 h-6 rounded-full transition-colors duration-300
              ${llmParams.thinking_enabled ? 'bg-primary' : 'bg-muted-foreground/20'}
            `}
          >
            <span
              className={`
                absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm
                transition-transform duration-300
                ${llmParams.thinking_enabled ? 'translate-x-5' : 'translate-x-0'}
              `}
            />
          </button>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium block">显示思考框</span>
            <span className="text-xs text-muted-foreground">控制界面是否显示思考过程</span>
          </div>
          <button
            onClick={toggleShowThinking}
            className={`
              relative w-11 h-6 rounded-full transition-colors duration-300
              ${showThinking ? 'bg-primary' : 'bg-muted-foreground/20'}
            `}
          >
            <span
              className={`
                absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm
                transition-transform duration-300
                ${showThinking ? 'translate-x-5' : 'translate-x-0'}
              `}
            />
          </button>
        </div>

        {/* RAG 模式开关 */}
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium block">RAG 模式</span>
            <span className="text-xs text-muted-foreground">启用记忆检索增强功能</span>
          </div>
          <button
            onClick={toggleRagMode}
            className={`
              relative w-11 h-6 rounded-full transition-colors duration-300
              ${ragMode ? 'bg-primary' : 'bg-muted-foreground/20'}
            `}
          >
            <span
              className={`
                absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm
                transition-transform duration-300
                ${ragMode ? 'translate-x-5' : 'translate-x-0'}
              `}
            />
          </button>
        </div>
      </div>

      {/* 压缩对话按钮 */}
      {currentSessionId && (
        <div className="pt-5 border-t border-border/50">
          <div className="bg-gradient-to-br from-blue-50 to-white dark:from-slate-800/50 dark:to-slate-800/30 rounded-2xl border border-blue-100 dark:border-slate-700 p-4">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 to-blue-500 flex items-center justify-center flex-shrink-0 shadow-md shadow-blue-500/20">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-sm text-foreground">对话压缩</h4>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  将当前对话历史压缩成摘要，保留关键信息的同时减少 Token 消耗
                </p>
              </div>
            </div>
            <Button
              onClick={compressSession}
              disabled={isStreaming}
              className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white border-0 rounded-xl shadow-md shadow-blue-500/25 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/30"
            >
              <Wrench className="w-4 h-4 mr-2" />
              {isStreaming ? '回复中，请稍候...' : '压缩当前对话'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

interface InspectorPanelProps {
  onCollapse?: () => void;
}

export function InspectorPanel({ onCollapse }: InspectorPanelProps) {
  const { 
    inspectorTab, 
    setInspectorTab, 
    inspectorFilePath, 
    setInspectorFilePath,
    theme,
    setTheme,
  } = useApp();

  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [skills, setSkills] = useState<api.Skill[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  
  const [selectedSkill, setSelectedSkill] = useState<api.Skill | null>(null);
  const [skillContent, setSkillContent] = useState("");
  const [isSkillLoading, setIsSkillLoading] = useState(false);
  const [skillPanelHeight, setSkillPanelHeight] = useState(60);
  const [isSkillDragging, setIsSkillDragging] = useState(false);

  const [filePanelHeight, setFilePanelHeight] = useState(60);
  const [isFileDragging, setIsFileDragging] = useState(false);

  // 模型配置面板显示状态
  const [showModelConfig, setShowModelConfig] = useState(false);
  const [modelConfigHeight, setModelConfigHeight] = useState(80);
  const [isModelConfigDragging, setIsModelConfigDragging] = useState(false);

  const handleModelConfigDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = modelConfigHeight;
    setIsModelConfigDragging(true);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      moveEvent.preventDefault();
      const container = document.querySelector('.flex-1.overflow-hidden') as HTMLElement;
      if (!container) return;

      const containerHeight = container.clientHeight;
      const deltaY = startY - moveEvent.clientY;
      const deltaPercent = (deltaY / containerHeight) * 100;
      const newHeight = Math.min(Math.max(startHeight + deltaPercent, 20), 85);

      requestAnimationFrame(() => {
        setModelConfigHeight(newHeight);
      });
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      setIsModelConfigDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove, { passive: false });
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  };

  const loadFile = useCallback(async (path: string) => {
    setIsLoading(true);
    try {
      const data = await api.readFile(path);
      setContent(data.content);
      setOriginalContent(data.content);
      setHasChanges(false);
    } catch (err) {
      console.error('Failed to load file:', err);
      setContent("");
      setOriginalContent("");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const saveFile = async () => {
    if (!inspectorFilePath) return;
    
    setIsSaving(true);
    try {
      await api.saveFile(inspectorFilePath, content);
      setOriginalContent(content);
      setHasChanges(false);
    } catch (err) {
      console.error('Failed to save file:', err);
      alert('保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  const loadSkills = useCallback(async () => {
    try {
      const data = await api.listSkills();
      setSkills(data);
    } catch (err) {
      console.error('Failed to load skills:', err);
    }
  }, []);

  const selectSkill = async (skill: api.Skill) => {
    setSelectedSkill(skill);
    setIsSkillLoading(true);
    try {
      const data = await api.readFile(skill.location);
      setSkillContent(data.content);
    } catch (err) {
      console.error('Failed to load skill file:', err);
      setSkillContent("加载失败");
    } finally {
      setIsSkillLoading(false);
    }
  };

  const closeSkillDetail = () => {
    setSelectedSkill(null);
    setSkillContent("");
    setSkillPanelHeight(60);
  };

  const closeFileDetail = () => {
    setInspectorFilePath(null);
    setContent("");
    setOriginalContent("");
    setFilePanelHeight(60);
  };

  const handleSkillDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = skillPanelHeight;
    setIsSkillDragging(true);
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      moveEvent.preventDefault();
      const container = document.querySelector('.flex-1.overflow-hidden') as HTMLElement;
      if (!container) return;
      
      const containerHeight = container.clientHeight;
      const deltaY = startY - moveEvent.clientY;
      const deltaPercent = (deltaY / containerHeight) * 100;
      const newHeight = Math.min(Math.max(startHeight + deltaPercent, 20), 85);
      
      requestAnimationFrame(() => {
        setSkillPanelHeight(newHeight);
      });
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      setIsSkillDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove, { passive: false });
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  };

  const handleFileDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = filePanelHeight;
    setIsFileDragging(true);
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      moveEvent.preventDefault();
      const container = document.querySelector('.flex-1.overflow-hidden') as HTMLElement;
      if (!container) return;
      
      const containerHeight = container.clientHeight;
      const deltaY = startY - moveEvent.clientY;
      const deltaPercent = (deltaY / containerHeight) * 100;
      const newHeight = Math.min(Math.max(startHeight + deltaPercent, 20), 85);
      
      requestAnimationFrame(() => {
        setFilePanelHeight(newHeight);
      });
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      setIsFileDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove, { passive: false });
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  };

  useEffect(() => {
    if (inspectorFilePath && inspectorTab === 'files') {
      loadFile(inspectorFilePath);
    }
  }, [inspectorFilePath, inspectorTab, loadFile]);

  useEffect(() => {
    setHasChanges(content !== originalContent);
  }, [content, originalContent]);

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  const renderFileTree = (nodes: FileNode[], level = 0) => {
    return nodes.map((node) => (
      <div key={node.path} style={{ paddingLeft: level * 12 }}>
        {node.type === 'dir' ? (
          <div>
            <div className="flex items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground">
              <FolderOpen className="w-4 h-4" />
              <span className="font-medium">{node.name}</span>
            </div>
            {node.children && renderFileTree(node.children, level + 1)}
          </div>
        ) : (
          <button
            onClick={() => {
              setInspectorFilePath(node.path);
              setInspectorTab('files');
            }}
            className={`
              w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-lg transition-all duration-200
              ${inspectorFilePath === node.path 
                ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400' 
                : 'hover:bg-slate-50 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800'
              }
            `}
          >
            <FileText className="w-4 h-4" />
            <span className="truncate">{node.name}</span>
          </button>
        )}
      </div>
    ));
  };

  const tabs = [
    { id: 'files', label: '文件', icon: FileText },
    { id: 'models', label: '模型', icon: Server },
    { id: 'settings', label: '设置', icon: Settings },
  ];

  // 主题切换按钮组
  const ThemeToggleGroup = () => (
    <div className="flex items-center bg-muted rounded-lg p-0.5">
      <button
        onClick={() => setTheme('light')}
        className={`
          p-1.5 rounded-md transition-all duration-200
          ${theme === 'light' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}
        `}
        title="浅色模式"
      >
        <Sun className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => setTheme('dark')}
        className={`
          p-1.5 rounded-md transition-all duration-200
          ${theme === 'dark' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}
        `}
        title="深色模式"
      >
        <Moon className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => setTheme('system')}
        className={`
          p-1.5 rounded-md transition-all duration-200
          ${theme === 'system' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}
        `}
        title="跟随系统"
      >
        <Monitor className="w-3.5 h-3.5" />
      </button>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-muted/20 border-l border-border/30 theme-transition relative">
      {/* 顶部工具栏 - 主题切换和收起按钮 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
        {/* 收起按钮 - 左上角 */}
        <button
          onClick={onCollapse}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200"
          title="收起右侧栏"
        >
          <PanelRight className="w-4 h-4" />
        </button>
        
        {/* 主题切换 */}
        <ThemeToggleGroup />
      </div>

      {/* Tab 导航 */}
      <div className="flex items-center border-b border-border/30 px-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => {
              setInspectorTab(id as typeof inspectorTab);
              // 切换 tab 时关闭所有悬浮窗
              setShowModelConfig(false);
              closeFileDetail();
              closeSkillDetail();
            }}
            className={`
              flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium
              transition-all duration-300 relative
              ${inspectorTab === id
                ? 'text-primary'
                : 'text-muted-foreground hover:text-foreground'
              }
            `}
          >
            <Icon className="w-4 h-4" />
            {label}
            {inspectorTab === id && (
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-blue-500 rounded-full animate-fade-in-scale" />
            )}
          </button>
        ))}
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden relative">
        {inspectorTab === 'settings' && (
          <ScrollArea className="h-full">
            <LLMSettingsPanel onOpenModelConfig={() => setShowModelConfig(true)} />
          </ScrollArea>
        )}

        {inspectorTab === 'models' && (
          <ScrollArea className="h-full">
            <ModelPanel onOpenModelConfig={() => setShowModelConfig(true)} />
          </ScrollArea>
        )}

        {inspectorTab === 'files' && (
          <>
            <ScrollArea className="h-full">
              <div className="p-3 space-y-4">
                {/* 技能列表 */}
                <div>
                  <div className="flex items-center justify-between px-2 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                    <span>技能</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={loadSkills}
                      className="h-6 w-6 rounded-lg hover:bg-muted"
                    >
                      <RefreshCw className="w-3 h-3" />
                    </Button>
                  </div>
                  <div className="space-y-1">
                    {skills.map((skill) => (
                      <button
                        key={skill.name}
                        onClick={() => selectSkill(skill)}
                        className={`
                          w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-lg transition-all duration-200
                          ${selectedSkill?.name === skill.name
                            ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                            : 'hover:bg-slate-50 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800'
                          }
                        `}
                      >
                        <Zap className="w-4 h-4" />
                        <span className="truncate">{skill.name}</span>
                      </button>
                    ))}
                    {skills.length === 0 && (
                      <div className="px-2 py-2 text-xs text-muted-foreground text-center">
                        暂无技能
                      </div>
                    )}
                  </div>
                </div>

                {/* 文件列表 */}
                <div>
                  <div className="px-2 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                    工作区文件
                  </div>
                  {renderFileTree(DEFAULT_FILES)}
                </div>
              </div>
            </ScrollArea>

            {/* 文件编辑器浮窗 */}
            {inspectorFilePath && (
              <div
                className="absolute inset-x-0 bottom-0 bg-card rounded-t-3xl shadow-[0_-8px_32px_rgba(0,0,0,0.12)] z-10 animate-slide-in-right border-t border-border/50"
                style={{ height: `${filePanelHeight}%` }}
              >
                <div
                  className={`
                    absolute top-0 left-0 right-0 h-7 flex items-center justify-center cursor-ns-resize z-20
                    transition-colors duration-200
                    ${isFileDragging ? 'bg-primary/5' : 'hover:bg-muted/50'}
                  `}
                  onMouseDown={handleFileDragStart}
                >
                  <div className={`
                    w-12 h-1 rounded-full transition-all duration-200
                    ${isFileDragging ? 'bg-primary w-16' : 'bg-muted-foreground/30'}
                  `} />
                </div>

                <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-muted/20 rounded-t-3xl mt-5">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                      <FileText className="w-4.5 h-4.5 text-primary" />
                    </div>
                    <span className="text-sm font-medium truncate max-w-[150px]">{inspectorFilePath}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      onClick={saveFile}
                      disabled={!hasChanges || isSaving}
                      className="rounded-lg bg-primary hover:bg-primary/90"
                    >
                      <Save className="w-4 h-4 mr-1.5" />
                      {isSaving ? '保存中...' : '保存'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={closeFileDetail}
                      className="rounded-lg hover:bg-muted"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="h-[calc(100%-70px-16px)] bg-card">
                  <Editor
                    height="100%"
                    language="markdown"
                    theme={theme === 'dark' ? 'vs-dark' : 'vs'}
                    value={content}
                    onChange={(value) => setContent(value || "")}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 13,
                      lineNumbers: 'on',
                      wordWrap: 'on',
                      scrollBeyondLastLine: false,
                      fontFamily: 'JetBrains Mono, monospace',
                      padding: { top: 16 },
                    }}
                    loading={
                      <div className="flex items-center justify-center h-full text-muted-foreground bg-card">
                        <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin mr-2" />
                        加载中...
                      </div>
                    }
                  />
                </div>
              </div>
            )}

            {/* 技能详情浮窗 */}
            {selectedSkill && (
              <div
                className="absolute inset-x-0 bottom-0 bg-card rounded-t-3xl shadow-[0_-8px_32px_rgba(0,0,0,0.12)] z-10 animate-slide-in-right border-t border-border/50"
                style={{ height: `${skillPanelHeight}%` }}
              >
                <div
                  className={`
                    absolute top-0 left-0 right-0 h-7 flex items-center justify-center cursor-ns-resize z-20
                    transition-colors duration-200
                    ${isSkillDragging ? 'bg-primary/5' : 'hover:bg-muted/50'}
                  `}
                  onMouseDown={handleSkillDragStart}
                >
                  <div className={`
                    w-12 h-1 rounded-full transition-all duration-200
                    ${isSkillDragging ? 'bg-primary w-16' : 'bg-muted-foreground/30'}
                  `} />
                </div>

                <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-muted/20 rounded-t-3xl mt-5">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                      <Code2 className="w-4.5 h-4.5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-medium text-sm">{selectedSkill.name}</h3>
                      <p className="text-xs text-muted-foreground">{selectedSkill.location}</p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={closeSkillDetail}
                    className="rounded-lg hover:bg-muted"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                <ScrollArea className="h-[calc(100%-70px-16px)]">
                  <div className="p-4">
                    {isSkillLoading ? (
                      <div className="flex items-center justify-center py-8 text-muted-foreground">
                        <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin mr-2" />
                        加载中...
                      </div>
                    ) : (
                      <pre className="whitespace-pre-wrap text-sm text-muted-foreground bg-muted/50 p-4 rounded-xl border border-border/30 font-mono text-xs leading-relaxed">
                        {skillContent}
                      </pre>
                    )}
                  </div>
                </ScrollArea>
              </div>
            )}
          </>
        )}
      </div>

      {/* 模型配置悬浮窗 */}
      {showModelConfig && (
        <div
          className="absolute inset-x-0 bottom-0 bg-card rounded-t-3xl shadow-[0_-8px_32px_rgba(0,0,0,0.12)] z-30 animate-slide-in-right border-t border-border/50"
          style={{ height: `${modelConfigHeight}%` }}
        >
          {/* 拖拽条 */}
          <div
            className={`
              absolute top-0 left-0 right-0 h-7 flex items-center justify-center cursor-ns-resize z-40
              transition-colors duration-200
              ${isModelConfigDragging ? 'bg-primary/5' : 'hover:bg-muted/50'}
            `}
            onMouseDown={handleModelConfigDragStart}
          >
            <div className={`
              w-12 h-1 rounded-full transition-all duration-200
              ${isModelConfigDragging ? 'bg-primary w-16' : 'bg-muted-foreground/30'}
            `} />
          </div>
          <div className="h-full pt-7">
            <ModelConfigPanel onClose={() => setShowModelConfig(false)} isFloating />
          </div>
        </div>
      )}
    </div>
  );
}
