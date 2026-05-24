"use client";

import { useState } from "react";
import { 
  CheckCircle2, 
  Circle, 
  Loader2, 
  AlertCircle, 
  ListTodo,
  ChevronDown,
  ChevronRight
} from "lucide-react";

export interface TodoItem {
  id: string;
  content: string;
  status: "pending" | "in_progress" | "completed" | "blocked";
  priority: "high" | "medium" | "low";
}

interface TodoListProps {
  todos: TodoItem[];
  completedCount?: number;
}

const statusConfig = {
  pending: {
    icon: Circle,
    label: "待处理",
    color: "text-slate-400",
    bgColor: "bg-slate-100 dark:bg-slate-800",
    borderColor: "border-slate-200 dark:border-slate-700",
  },
  in_progress: {
    icon: Loader2,
    label: "进行中",
    color: "text-blue-500",
    bgColor: "bg-blue-50 dark:bg-blue-950/30",
    borderColor: "border-blue-200 dark:border-blue-800",
  },
  completed: {
    icon: CheckCircle2,
    label: "已完成",
    color: "text-emerald-500",
    bgColor: "bg-emerald-50 dark:bg-emerald-950/30",
    borderColor: "border-emerald-200 dark:border-emerald-800",
  },
  blocked: {
    icon: AlertCircle,
    label: "被阻塞",
    color: "text-amber-500",
    bgColor: "bg-amber-50 dark:bg-amber-950/30",
    borderColor: "border-amber-200 dark:border-amber-800",
  },
};

const priorityConfig = {
  high: { label: "高", color: "text-red-500 bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800" },
  medium: { label: "中", color: "text-amber-500 bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800" },
  low: { label: "低", color: "text-slate-500 bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700" },
};

export function TodoList({ todos, completedCount }: TodoListProps) {
  const [expanded, setExpanded] = useState(true);

  if (!todos || todos.length === 0) return null;

  const completed = completedCount ?? todos.filter(t => t.status === "completed").length;
  const total = todos.length;

  return (
    <div className="mt-3 bg-gradient-to-br from-slate-50/80 to-slate-100/50 dark:from-slate-900/50 dark:to-slate-800/30 border border-slate-200/70 dark:border-slate-700/50 rounded-xl overflow-hidden animate-fade-in-up">
      {/* 头部 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-100/50 dark:hover:bg-slate-800/30 transition-colors"
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-sm">
          <ListTodo className="w-4 h-4 text-white" />
        </div>
        
        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              任务列表
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-medium">
              {completed}/{total}
            </span>
          </div>
          <div className="mt-1.5 h-1.5 w-32 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all duration-500"
              style={{ width: `${total > 0 ? (completed / total) * 100 : 0}%` }}
            />
          </div>
        </div>

        {expanded ? (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {/* 任务列表 */}
      {expanded && (
        <div className="px-3 pb-3 space-y-1.5">
          {todos.map((todo, index) => {
            const status = statusConfig[todo.status];
            const priority = priorityConfig[todo.priority];
            const Icon = status.icon;
            const isInProgress = todo.status === "in_progress";

            return (
              <div
                key={todo.id}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-all duration-300
                  ${isInProgress 
                    ? 'bg-blue-50/70 dark:bg-blue-950/20 border-blue-200/70 dark:border-blue-900/40 shadow-sm' 
                    : 'bg-white/60 dark:bg-slate-800/40 border-slate-200/50 dark:border-slate-700/30 hover:bg-white/80 dark:hover:bg-slate-800/60'}
                `}
                style={{ animationDelay: `${index * 50}ms` }}
              >
                {/* 状态图标 */}
                <div className={`
                  w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0
                  ${todo.status === "completed" 
                    ? "bg-emerald-100 dark:bg-emerald-900/30" 
                    : todo.status === "in_progress"
                    ? "bg-blue-100 dark:bg-blue-900/30"
                    : todo.status === "blocked"
                    ? "bg-amber-100 dark:bg-amber-900/30"
                    : "bg-slate-100 dark:bg-slate-700"}
                `}>
                  <Icon 
                    className={`w-3.5 h-3.5 ${status.color} ${isInProgress ? 'animate-spin' : ''}`} 
                    style={{ animationDuration: isInProgress ? '2s' : '0s' }}
                  />
                </div>

                {/* 任务内容 */}
                <div className="flex-1 min-w-0">
                  <p className={`
                    text-sm truncate
                    ${todo.status === "completed" 
                      ? "text-slate-500 dark:text-slate-400 line-through" 
                      : "text-slate-700 dark:text-slate-200"}
                  `}>
                    {todo.content}
                  </p>
                </div>

                {/* 优先级标签 */}
                <span className={`
                  text-[10px] px-1.5 py-0.5 rounded border font-medium flex-shrink-0
                  ${priority.color}
                `}>
                  {priority.label}
                </span>

                {/* 状态标签 */}
                <span className={`
                  text-[10px] px-2 py-0.5 rounded-full font-medium flex-shrink-0
                  ${status.bgColor} ${status.color} border ${status.borderColor}
                `}>
                  {status.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
