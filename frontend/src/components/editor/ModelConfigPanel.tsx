"use client";

import { useState } from "react";
import {
  X,
  Plus,
  Trash2,
  Check,
  AlertCircle,
  Server,
  Layers,
  GitBranch,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Brain,
  Save,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useApp } from "@/lib/store";
import { ModelType, ModelConfig } from "@/lib/types";

interface ModelConfigPanelProps {
  onClose: () => void;
  isFloating?: boolean;
}

// 可折叠的模型配置面板
function CollapsibleModelPanel({
  title,
  icon: Icon,
  isExpanded,
  onToggle,
  children,
}: {
  title: string;
  icon: React.ElementType;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 bg-muted/30 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">{title}</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>
      {isExpanded && <div className="p-4 space-y-4">{children}</div>}
    </div>
  );
}

// 新建模型表单
function AddModelForm({
  onSave,
  onCancel,
  onTest,
  isTesting,
  testResult,
}: {
  onSave: (config: {
    name: string;
    model: string;
    api_key: string;
    base_url: string;
  }) => void;
  onCancel: () => void;
  onTest: (config: {
    model: string;
    api_key: string;
    base_url: string;
  }) => void;
  isTesting: boolean;
  testResult: { success: boolean; message: string } | null;
}) {
  const [form, setForm] = useState({
    name: "",
    model: "",
    api_key: "",
    base_url: "",
  });

  const handleTest = () => {
    if (form.model && form.api_key && form.base_url) {
      onTest({ model: form.model, api_key: form.api_key, base_url: form.base_url });
    }
  };

  const handleSave = () => {
    if (form.name && form.model && form.api_key && form.base_url) {
      onSave(form);
    }
  };

  const isValid = form.name && form.model && form.api_key && form.base_url;

  return (
    <div className="space-y-4 p-4 bg-muted/30 rounded-xl border border-border/50">
      <h4 className="text-sm font-medium flex items-center gap-2">
        <Plus className="w-4 h-4" />
        新建模型
      </h4>

      <div className="space-y-3">
        <div>
          <label className="text-xs text-muted-foreground block mb-1.5">
            显示名称
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="例如：GPT-4o"
            className="w-full px-3 py-2 text-sm bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div>
          <label className="text-xs text-muted-foreground block mb-1.5">
            模型 ID
          </label>
          <input
            type="text"
            value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
            placeholder="例如：gpt-4o"
            className="w-full px-3 py-2 text-sm bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div>
          <label className="text-xs text-muted-foreground block mb-1.5">
            Base URL
          </label>
          <input
            type="text"
            value={form.base_url}
            onChange={(e) => setForm({ ...form, base_url: e.target.value })}
            placeholder="例如：https://api.openai.com/v1"
            className="w-full px-3 py-2 text-sm bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div>
          <label className="text-xs text-muted-foreground block mb-1.5">
            API Key
          </label>
          <input
            type="password"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            placeholder="sk-..."
            className="w-full px-3 py-2 text-sm bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* 测试结果 */}
      {testResult && (
        <div
          className={`flex items-center gap-2 text-xs p-2 rounded-lg ${
            testResult.success
              ? "bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400"
              : "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400"
          }`}
        >
          {testResult.success ? (
            <Check className="w-4 h-4" />
          ) : (
            <AlertCircle className="w-4 h-4" />
          )}
          {testResult.message}
        </div>
      )}

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleTest}
          disabled={!form.model || !form.api_key || !form.base_url || isTesting}
          className="flex-1"
        >
          {isTesting ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              测试中...
            </>
          ) : (
            <>
              <Server className="w-3.5 h-3.5 mr-1.5" />
              测试连接
            </>
          )}
        </Button>
        <Button variant="outline" size="sm" onClick={onCancel}>
          取消
        </Button>
        <Button
          size="sm"
          onClick={handleSave}
          disabled={!isValid}
          className="bg-primary hover:bg-primary/90"
        >
          <Save className="w-3.5 h-3.5 mr-1.5" />
          保存
        </Button>
      </div>
    </div>
  );
}

// 模型列表项
function ModelListItem({
  model,
  isCurrent,
  onSetCurrent,
  onSetDefault,
  onDelete,
}: {
  model: ModelConfig;
  isCurrent: boolean;
  onSetCurrent: () => void;
  onSetDefault: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border ${
        isCurrent
          ? "bg-primary/5 border-primary/20"
          : "bg-muted/20 border-border/30 hover:bg-muted/30"
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{model.name}</span>
          {model.is_default && (
            <span className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded-full">
              默认
            </span>
          )}
          {isCurrent && (
            <span className="text-[10px] px-1.5 py-0.5 bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400 rounded-full">
              当前
            </span>
          )}
        </div>
        <div className="text-xs text-muted-foreground truncate mt-0.5">
          {model.model}
        </div>
      </div>
      <div className="flex items-center gap-1 ml-2">
        {!isCurrent && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onSetCurrent}
            className="h-7 w-7"
            title="设为当前模型"
          >
            <Check className="w-3.5 h-3.5" />
          </Button>
        )}
        {!model.is_default && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onSetDefault}
            className="h-7 w-7"
            title="设为默认"
          >
            <Save className="w-3.5 h-3.5" />
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onDelete}
          className="h-7 w-7 text-destructive hover:text-destructive"
          title="删除"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>
  );
}

export function ModelConfigPanel({ onClose, isFloating }: ModelConfigPanelProps) {
  const {
    modelConfigs,
    setCurrentModel,
    setDefaultModel,
    deleteModelConfig,
    addModelConfig,
    testModelConnection,
    loadModelConfigs,
  } = useApp();

  // 展开状态
  const [expandedPanels, setExpandedPanels] = useState({
    llm: true, // LLM 默认展开
    embedding: false, // Embedding 默认折叠
    rerank: false, // Rerank 默认折叠
  });

  // 新建模型表单显示状态
  const [showAddForm, setShowAddForm] = useState<{ [key in ModelType]?: boolean }>({});

  // 测试状态
  const [testingModel, setTestingModel] = useState<ModelType | null>(null);
  const [testResults, setTestResults] = useState<{
    [key: string]: { success: boolean; message: string } | null;
  }>({});

  const togglePanel = (panel: keyof typeof expandedPanels) => {
    setExpandedPanels((prev) => ({ ...prev, [panel]: !prev[panel] }));
  };

  const handleTestConnection = async (
    modelType: ModelType,
    config: { model: string; api_key: string; base_url: string }
  ) => {
    setTestingModel(modelType);
    const result = await testModelConnection(modelType, config);
    setTestResults((prev) => ({ ...prev, [modelType]: result }));
    setTestingModel(null);
  };

  const handleAddModel = async (
    modelType: ModelType,
    config: { name: string; model: string; api_key: string; base_url: string }
  ) => {
    await addModelConfig(modelType, config);
    setShowAddForm((prev) => ({ ...prev, [modelType]: false }));
    setTestResults((prev) => ({ ...prev, [modelType]: null }));
  };

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-muted/20">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
            <Server className="w-4.5 h-4.5 text-primary" />
          </div>
          <div>
            <h2 className="font-medium text-sm text-foreground">模型配置</h2>
            <p className="text-xs text-muted-foreground">
              管理 LLM、Embedding 和 Rerank 模型
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={loadModelConfigs}
            disabled={modelConfigs.isLoading}
            className="rounded-lg"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 mr-1.5 ${
                modelConfigs.isLoading ? "animate-spin" : ""
              }`}
            />
            刷新
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-lg hover:bg-muted">
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* 内容区域 */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* LLM 模型配置 - 默认展开 */}
          <CollapsibleModelPanel
            title="LLM 模型"
            icon={Brain}
            isExpanded={expandedPanels.llm}
            onToggle={() => togglePanel("llm")}
          >
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground">
                模型列表
              </div>
              {modelConfigs.llmModels.map((model) => (
                <ModelListItem
                  key={model.id}
                  model={model}
                  isCurrent={model.id === modelConfigs.currentLLMModelId}
                  onSetCurrent={() => setCurrentModel("llm", model.id)}
                  onSetDefault={() => setDefaultModel("llm", model.id)}
                  onDelete={() => deleteModelConfig("llm", model.id)}
                />
              ))}
            </div>

            {showAddForm.llm ? (
              <AddModelForm
                onSave={(config) => handleAddModel("llm", config)}
                onCancel={() =>
                  setShowAddForm((prev) => ({ ...prev, llm: false }))
                }
                onTest={(config) => handleTestConnection("llm", config)}
                isTesting={testingModel === "llm"}
                testResult={testResults.llm}
              />
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setShowAddForm((prev) => ({ ...prev, llm: true }))
                }
                className="w-full"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                添加 LLM 模型
              </Button>
            )}
          </CollapsibleModelPanel>

          {/* Embedding 模型配置 - 默认折叠 */}
          <CollapsibleModelPanel
            title="Embedding 模型"
            icon={Layers}
            isExpanded={expandedPanels.embedding}
            onToggle={() => togglePanel("embedding")}
          >
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground">
                模型列表
              </div>
              {modelConfigs.embeddingModels.map((model) => (
                <ModelListItem
                  key={model.id}
                  model={model}
                  isCurrent={model.id === modelConfigs.currentEmbeddingModelId}
                  onSetCurrent={() => setCurrentModel("embedding", model.id)}
                  onSetDefault={() => setDefaultModel("embedding", model.id)}
                  onDelete={() => deleteModelConfig("embedding", model.id)}
                />
              ))}
            </div>

            {showAddForm.embedding ? (
              <AddModelForm
                onSave={(config) => handleAddModel("embedding", config)}
                onCancel={() =>
                  setShowAddForm((prev) => ({ ...prev, embedding: false }))
                }
                onTest={(config) => handleTestConnection("embedding", config)}
                isTesting={testingModel === "embedding"}
                testResult={testResults.embedding}
              />
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setShowAddForm((prev) => ({ ...prev, embedding: true }))
                }
                className="w-full"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                添加 Embedding 模型
              </Button>
            )}
          </CollapsibleModelPanel>

          {/* Rerank 模型配置 - 默认折叠 */}
          <CollapsibleModelPanel
            title="Rerank 模型"
            icon={GitBranch}
            isExpanded={expandedPanels.rerank}
            onToggle={() => togglePanel("rerank")}
          >
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground">
                模型列表
              </div>
              {modelConfigs.rerankModels.map((model) => (
                <ModelListItem
                  key={model.id}
                  model={model}
                  isCurrent={model.id === modelConfigs.currentRerankModelId}
                  onSetCurrent={() => setCurrentModel("rerank", model.id)}
                  onSetDefault={() => setDefaultModel("rerank", model.id)}
                  onDelete={() => deleteModelConfig("rerank", model.id)}
                />
              ))}
            </div>

            {showAddForm.rerank ? (
              <AddModelForm
                onSave={(config) => handleAddModel("rerank", config)}
                onCancel={() =>
                  setShowAddForm((prev) => ({ ...prev, rerank: false }))
                }
                onTest={(config) => handleTestConnection("rerank", config)}
                isTesting={testingModel === "rerank"}
                testResult={testResults.rerank}
              />
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setShowAddForm((prev) => ({ ...prev, rerank: true }))
                }
                className="w-full"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                添加 Rerank 模型
              </Button>
            )}
          </CollapsibleModelPanel>
        </div>
      </ScrollArea>
    </div>
  );
}
