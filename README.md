# Simple Agent

<div align="center">

**一个轻量级、全透明的 AI Agent 系统**

*文件即记忆 · 技能即插件 · 全程可视化*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-orange.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 项目简介

Simple Agent 是一个强调**透明性**和**可控性**的 AI Agent 系统。与传统的"黑盒"Agent 不同，它将所有数据以文件形式存储，所有操作过程完全可视化，让用户真正掌控 AI 的每一个决策。

### 核心理念

| 传统 Agent | Simple Agent |
|------------|---------------|
| 向量数据库存储记忆 | Markdown/JSON 文件存储 |
| Function Calling 调用技能 | 指令式技能定义 |
| 黑盒操作过程 | 全透明可追溯 |
| 依赖外部数据库 | 本地文件系统优先 |

---

## ✨ 核心特性

### 🗂️ 文件即记忆 (File-first Memory)

所有记忆以 Markdown/JSON 文件形式存储，确保完全的数据主权和可解释性：

```
workspace/
├── SOUL.md       # 人格、语气、边界
├── IDENTITY.md   # 名称、风格
├── USER.md       # 用户画像
├── AGENTS.md     # 操作指南 & 协议
└── MEMORY.md     # 长期记忆
```

### 🔌 技能即插件 (Skills as Plugins)

通过 Markdown 指令文件扩展能力，拖入即用：

```
workspace/skills/
└── get_weather/
    └── SKILL.md   # 技能定义文件
```

### 🔍 全透明可控

- **System Prompt 可视化**：查看完整的 Prompt 拼接过程
- **工具调用追踪**：每个工具的输入输出都有记录
- **记忆读写透明**：所有记忆操作可追溯
- **LLM 请求调试**：查看发送给 LLM 的完整请求

### 🎯 其他特性

- **多模态支持**：支持文本 + 图片混合输入
- **智能对话压缩**：自动压缩历史对话，降低 Token 消耗
- **IDE 风格界面**：三栏式布局，集成 Monaco Editor 实时编辑
- **多模型管理**：支持配置多个 LLM/Embedding/Rerank 模型
- **RAG 模式**：基于 LlamaIndex 的记忆检索增强

---

## 🛠️ 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| FastAPI 0.115 + Uvicorn 0.32 | Web 框架 |
| LangChain 0.3 + langchain-community 0.3 | Agent 引擎 |
| LlamaIndex Core 0.12 | 向量检索 |
| tiktoken 0.8 | Token 计数 |
| Pydantic 2.9 + pydantic-settings 2.6 | 数据验证 |
| BeautifulSoup4 + html2text | HTML 处理 |
| requests 2.32 | HTTP 请求 |
| python-multipart 0.0.17 | 文件上传 |
| PyYAML 6.0 | YAML 解析 |

### 前端

| 技术 | 用途 |
|------|------|
| Next.js 15.2 | React 框架 |
| React 19 + React-DOM 19 | UI 库 |
| TypeScript 5.8 | 类型安全 |
| Tailwind CSS 3.4 | 样式 |
| Radix UI | 无障碍组件 |
| Monaco Editor 0.52 | 代码编辑器 |
| react-markdown + remark-gfm | Markdown 渲染 |
| lucide-react | 图标库 |
| class-variance-authority + clsx | 样式变体 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- API Key（支持 OpenAI 兼容接口）

### 1. 获取项目

```bash
git clone https://github.com/qwqk423/Simple-agent.git
cd Simple-agent
```

### 2. 配置后端

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
```

编辑 `.env` 文件：

```env
# LLM API 配置 (OpenAI 兼容接口)
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=qwen3.5-27b

# Embedding API 配置 (可选，默认使用 LLM 配置)
EMBEDDING_API_KEY=sk-your-api-key
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-v4

# Rerank API 配置 (可选)
RERANK_API_KEY=sk-your-api-key
RERANK_BASE_URL=https://api.openai.com/v1
RERANK_MODEL=qwen3-vl-rerank
```

### 3. 启动后端

```bash
python app.py
```

后端服务将在 http://localhost:8080 运行

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端服务将在 http://localhost:3000 运行

### 5. 访问应用

打开浏览器访问 http://localhost:3000

---

## 📁 项目结构

```
Simple-agent/
├── backend/                    # FastAPI 后端
│   ├── app.py                 # 应用入口
│   ├── config.py              # 全局配置管理
│   ├── config.json            # 运行时配置
│   ├── requirements.txt       # Python 依赖
│   ├── SKILLS_SNAPSHOT.md     # 技能快照（自动生成）
│   ├── test_tools.py          # 工具测试脚本
│   ├── .env                   # 环境变量配置
│   ├── .env.example           # 环境变量示例
│   │
│   ├── api/                   # API 路由层
│   │   ├── chat.py            # SSE 流式对话
│   │   ├── sessions.py        # 会话管理
│   │   ├── files.py           # 文件操作
│   │   ├── config_api.py      # 配置管理 API
│   │   ├── compress.py        # 对话压缩
│   │   └── tokens.py          # Token 统计
│   │
│   ├── graph/                 # Agent 核心逻辑
│   │   ├── __init__.py
│   │   ├── agent.py           # Agent 管理器（REPL 循环）
│   │   ├── session_manager.py # 双文件会话持久化
│   │   ├── prompt_builder.py  # System Prompt 组装
│   │   ├── memory_indexer.py  # 记忆向量索引
│   │   ├── codebase_indexer.py# 代码库索引
│   │   └── title_generator.py # 会话标题生成
│   │
│   ├── tools/                 # 15 个核心工具
│   │   ├── __init__.py
│   │   ├── skills_scanner.py  # 技能扫描器
│   │   ├── terminal_tool.py       # 沙箱终端
│   │   ├── python_repl_tool.py    # Python 解释器
│   │   ├── fetch_url_tool.py      # 网页抓取
│   │   ├── read_file_tool.py      # 文件读取
│   │   ├── write_file_tool.py     # 文件写入
│   │   ├── edit_file_tool.py      # 文件编辑
│   │   ├── apply_diff_tool.py     # 代码差异应用
│   │   ├── grep_tool.py           # 文本搜索
│   │   ├── glob_tool.py           # 文件模式匹配
│   │   ├── search_codebase_tool.py# 代码库语义搜索
│   │   ├── search_knowledge_tool.py# 知识库搜索
│   │   ├── list_workspace_tool.py # 目录列表
│   │   ├── todo_tool.py           # 待办事项管理
│   │   └── finish_tool.py         # 会话结束标记
│   │
│   ├── utils/                 # 工具函数
│   │   ├── __init__.py
│   │   ├── llm_factory.py     # LLM 实例工厂
│   │   ├── embedding_adapter.py# Embedding 适配器
│   │   ├── rerank_adapter.py  # Rerank 适配器
│   │   └── logger.py          # 日志工具
│   │
│   ├── workspace/             # System Prompt 组件
│   │   ├── SOUL.md            # 人格定义
│   │   ├── IDENTITY.md        # 身份信息
│   │   ├── USER.md            # 用户画像
│   │   ├── AGENTS.md          # 操作指南
│   │   ├── MEMORY.md          # 长期记忆
│   │   ├── BOOTSTRAP.md       # 启动引导
│   │   └── skills/            # 技能目录
│   │       └── get_weather/
│   │           └── SKILL.md
│   │
│   ├── sessions/              # 会话存储
│   │   ├── efficient/         # 压缩后记录
│   │   └── original/          # 完整对话记录
│   │
│   └── logs/                  # 日志目录
│       └── app.log
│
└── frontend/                  # Next.js 前端
    ├── src/
    │   ├── app/               # 页面
    │   │   ├── globals.css
    │   │   ├── layout.tsx
    │   │   └── page.tsx
    │   ├── components/        # 组件
    │   │   ├── chat/          # 聊天组件
    │   │   ├── layout/        # 布局组件
    │   │   ├── editor/        # 编辑器组件
    │   │   ├── compress/      # 压缩组件
    │   │   └── ui/            # UI 组件
    │   └── lib/               # 工具函数
    │       ├── api.ts
    │       ├── logger.ts
    │       ├── store.tsx
    │       ├── types.ts
    │       └── utils.ts
    ├── next.config.js
    ├── package.json
    ├── postcss.config.js
    ├── tailwind.config.js
    └── tsconfig.json
```

---

## 🔧 核心工具

### 1. skills_scanner - 技能扫描器

扫描 `workspace/skills/` 目录下的技能定义文件，生成 `SKILLS_SNAPSHOT.md` 供 Agent 了解可用技能。

```python
# 示例
skills_scanner(skills_dir="workspace/skills")
```

**工作流程：**
1. 扫描 `workspace/skills/{skill_name}/SKILL.md` 文件
2. 解析 Markdown frontmatter 获取技能元信息
3. 生成技能快照到 `SKILLS_SNAPSHOT.md`
4. Agent 通过读取快照了解可用技能

### 2. terminal - 沙箱命令行

执行 Shell 命令，支持安全限制。

```python
# 示例
terminal(commands="ls -la")
terminal(commands="npm install")
```

**限制**：
- 30 秒超时
- 输出最多 5000 字符
- 高危命令黑名单（rm -rf /, mkfs 等）

### 3. python_repl - Python 解释器

执行 Python 代码，用于逻辑计算和数据处理。

```python
# 示例
python_repl(code="print(sum(range(100)))")
```

### 4. fetch_url - 网页抓取

获取网页内容，自动 HTML 转 Markdown。

```python
# 示例
fetch_url(url="https://example.com")
```

### 4. read_file - 文件读取

读取项目内文件，支持路径遍历防护。

```python
# 示例
read_file(file_path="workspace/MEMORY.md")
```

### 5. write_file - 文件写入

写入文件，自动创建父目录。

```python
# 示例
write_file(file_path="output/result.txt", content="Hello World")
```

### 7. apply_diff - 代码差异应用

使用 SEARCH/REPLACE 格式精确修改代码。

```python
# 示例
apply_diff(
    file_path="src/app.py",
    old_str="def hello():\n    pass",
    new_str="def hello():\n    print('Hello')"
)
```

### 8. edit_file - 快速文件编辑

快速小修改文件内容（10行以内），如修改变量名、修复 bug、调整单行逻辑。

```python
# 示例
edit_file(
    path="src/config.py",
    old_str="debug = False",
    new_str="debug = True"
)
```

**与 apply_diff 的区别：**
| 场景 | 推荐工具 | 原因 |
|------|----------|------|
| 小修改（<10行） | edit_file | 简单直接，操作快捷 |
| 大修改/重构 | apply_diff | 支持多段替换，结构化 |

**限制：**
- old_str 必须完全匹配（包括缩进和换行）
- 只能替换唯一匹配的位置

### 9. grep - 文本搜索

基于 ripgrep 的文件内容搜索，支持正则表达式。

```python
# 示例
grep(pattern="TODO", path="src/", output_mode="content")
```

### 10. glob - 文件模式匹配

按文件名模式匹配查找文件。

```python
# 示例
glob(pattern="**/*.py")
```

### 10. search_codebase - 代码库语义搜索

基于自然语言的代码搜索，使用向量检索 + Rerank。

```python
# 示例
search_codebase(
    information_request="用户认证的实现代码",
    project="my-backend",
    top_k=5
)
```

### 10. search_knowledge_base - 知识库搜索

LlamaIndex 向量检索，支持 PDF/MD/TXT 文件。

```python
# 示例
search_knowledge_base(query="项目架构说明")
```

### 12. list_workspace - 目录列表

列出指定目录内容，支持递归。

```python
# 示例
list_workspace(path="workspace/code")
```

### 12. todo_write - 待办事项管理

结构化任务管理，实时同步到前端。

```python
# 示例
todo_write(todos=[
    {"id": "1", "content": "实现功能", "status": "pending", "priority": "high"}
])
```

### 15. finish - 会话结束标记

标记任务完成，终止 REPL 循环。

```python
# 示例
finish(summary="任务已完成")
```

---

## 🌐 API 接口

### 对话相关

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式对话 |
| `/api/chat/last-request` | GET | 获取最后 LLM 请求（调试） |

### 会话管理

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/sessions` | GET | 列出所有会话 |
| `/api/sessions` | POST | 创建新会话 |
| `/api/sessions/{id}` | PUT | 重命名会话 |
| `/api/sessions/{id}` | DELETE | 删除会话 |
| `/api/sessions/{id}/history` | GET | 获取对话历史 |
| `/api/sessions/{id}/compress` | GET | 获取压缩预览 |
| `/api/sessions/{id}/compress` | POST | 执行对话压缩 |

### 文件操作

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/files?path=...` | GET | 读取文件 |
| `/api/files` | POST | 保存文件 |

### 配置管理

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/config/llm-params` | GET/PUT | LLM 参数管理 |
| `/api/config/rag-mode` | GET/PUT | RAG 模式开关 |
| `/api/models/{type}` | GET | 获取模型列表 |
| `/api/models/{type}` | POST | 添加模型 |
| `/api/models/{type}/{id}` | PUT | 更新模型 |
| `/api/models/{type}/{id}` | DELETE | 删除模型 |

### 技能管理

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/skills` | GET | 列出技能 |

---

## ⚙️ 配置说明

### 后端配置 (.env)

```env
# LLM API 配置
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=qwen3.5-27b

# Embedding 配置（可选）
EMBEDDING_API_KEY=sk-your-api-key
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-v4

# Rerank 配置（可选）
RERANK_API_KEY=sk-your-api-key
RERANK_BASE_URL=https://api.openai.com/v1
RERANK_MODEL=qwen3-vl-rerank
```

### 运行时配置 (config.json)

可通过 API 或前端界面实时调整：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `temperature` | float | 0.7 | 随机性（0-2） |
| `top_p` | float | 0.8 | 核采样（0-1） |
| `presence_penalty` | float | 0.0 | 存在惩罚（-2 到 2） |
| `max_tokens` | int | 8192 | 最大生成长度 |
| `thinking_enabled` | bool | true | 思考模式开关 |
| `rag_mode` | bool | false | RAG 模式开关 |

### 前端配置

前端通过环境变量配置后端 API 地址：

```env
# .env.local 或部署平台环境变量
NEXT_PUBLIC_API_URL=https://your-backend-url  # 可选，不设置则使用默认值
```

**默认行为**：
- 浏览器环境：自动使用当前域名 + `:8080` 端口
- 服务端渲染：默认 `http://localhost:8080`

**next.config.js 配置**：

```javascript
const nextConfig = {
  output: 'standalone',  // Docker 部署优化
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
  },
};
```

---

## 📖 使用指南

### 创建新对话

点击左侧边栏的「新对话」按钮开始对话。

### 使用技能

1. Agent 自动读取 `SKILLS_SNAPSHOT.md` 了解可用技能
2. 需要时调用 `read_file` 读取技能定义
3. 根据技能定义执行相应操作

### RAG 模式

1. 在右侧检查器面板开启「RAG 模式」
2. Agent 会在每次对话前检索 `MEMORY.md` 相关内容
3. 检索结果显示在聊天界面中

### 编辑记忆文件

1. 点击右侧检查器的「文件」标签
2. 选择目标文件（如 `MEMORY.md`）
3. 在 Monaco Editor 中编辑
4. 点击「保存」

### 压缩对话

当对话历史过长时：

1. 点击左侧边栏的「压缩对话」按钮
2. 系统保留最近 2 轮对话
3. 调用 LLM 生成前面内容的摘要
4. 压缩后记录用于 LLM 请求，原始记录保留用于显示

### 调试 LLM 请求

点击左侧边栏的「最后请求」按钮，查看发送给 LLM 的完整请求内容。

### 调整 LLM 参数

在右侧检查器面板的「设置」标签中实时调整参数。

---

## 🎨 界面功能

### 三栏式布局

```
┌────────────┬──────────────────────┬────────────┐
│            │                      │            │
│   侧边栏    │       聊天区域        │   检查器    │
│            │                      │            │
│  · 会话     │  · 消息列表           │  · 文件     │
│  · 压缩     │  · 工具调用展示        │  · 模型    │
│  · 调试     │  · 思考过程展示        │  · 设置    │
│            │  · 输入框             │            │
│            │                      │            │
└────────────┴──────────────────────┴────────────┘
```

### 主要功能

- **会话管理**：创建、切换、重命名、删除会话
- **消息展示**：支持 Markdown 渲染、代码高亮
- **工具调用可视化**：展示工具名称、输入、输出
- **思考过程展示**：可折叠的思考内容区域
- **待办事项面板**：实时同步 Agent 的任务列表
- **Monaco Editor**：实时编辑工作区文件
- **主题切换**：支持浅色/深色/跟随系统

---

## 🔒 安全说明

### 终端工具限制

- 高危命令黑名单
- 30 秒超时
- 输出截断（5000 字符）

### 文件操作限制

- 路径遍历防护
- 只能访问项目目录内文件

### 网络请求限制

- fetch_url 工具 15 秒超时
- 仅支持 HTTP/HTTPS 协议

---

## 🐛 故障排除

### 后端启动失败

1. 检查 Python 版本（需要 3.10+）
2. 检查依赖安装：`pip install -r requirements.txt`
3. 检查 `.env` 文件配置

### 前端启动失败

1. 检查 Node.js 版本（需要 18+）
2. 删除 node_modules 重新安装：
   ```bash
   rm -rf node_modules && npm install
   ```

### AI 对话无响应

1. 检查后端是否运行：`curl http://localhost:8080/health`
2. 检查 API Key 是否有效
3. 查看后端日志错误信息

### RAG 功能不工作

1. 确认 `workspace/MEMORY.md` 文件存在且有内容
2. 检查索引是否成功构建
3. 确认 RAG 模式已开启

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - Agent 框架
- [LlamaIndex](https://github.com/run-llama/llama_index) - RAG 框架
- [FastAPI](https://github.com/tiangolo/fastapi) - Web 框架
- [Next.js](https://github.com/vercel/next.js) - 前端框架
- [Monaco Editor](https://github.com/microsoft/monaco-editor) - 代码编辑器

---

<div align="center">

**Made with ❤️ by Simple Agent Team**

</div>
