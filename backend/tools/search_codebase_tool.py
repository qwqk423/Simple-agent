"""代码库语义搜索工具 - 基于向量检索 + Rerank 的智能代码检索"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

# 确保 backend 目录在路径中
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from config import settings
from graph.codebase_indexer import get_codebase_indexer, CodebaseIndexerManager
from utils.rerank_adapter import create_reranker
from utils.logger import get_logger

logger = get_logger("SearchCodebaseTool")


class SearchCodebaseInput(BaseModel):
    """代码库语义搜索工具的输入参数"""
    information_request: str = Field(
        description="自然语言描述的代码搜索请求，例如：'查找用户认证的实现代码'"
    )
    project: Optional[str] = Field(
        default=None,
        description="指定要搜索的项目名称（workspace/code 下的文件夹名），不指定则搜索所有项目"
    )
    top_k: int = Field(
        default=5,
        description="返回的结果数量，默认5个"
    )


class CodebaseSearchTool:
    """代码库搜索工具核心类"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.code_dir = base_dir / "workspace" / "code"
        self.indexer: Optional[CodebaseIndexerManager] = None
        self.reranker = None
        self._initialized = False

    def _lazy_init(self):
        """延迟初始化 - 只在第一次使用时初始化"""
        if self._initialized:
            return
        
        try:
            self.indexer = get_codebase_indexer(self.base_dir)
            logger.debug(f"代码库索引管理器初始化成功: {self.base_dir}")
        except Exception as e:
            logger.error(f"代码库索引管理器初始化失败: {type(e).__name__}: {e}")
            self._initialized = True
            return

        try:
            rerank_api_key = settings.rerank_api_key if settings.rerank_api_key else settings.openai_api_key
            rerank_base_url = settings.rerank_base_url if settings.rerank_base_url else settings.openai_base_url
            self.reranker = create_reranker(
                api_key=rerank_api_key,
                base_url=rerank_base_url
            )
            logger.debug("Reranker 初始化成功")
        except Exception as e:
            logger.error(f"Reranker 初始化失败: {type(e).__name__}: {e}")
        
        self._initialized = True
    
    def _format_code_snippet(self, text: str, max_lines: int = 15) -> str:
        """格式化代码片段，限制行数"""
        lines = text.split('\n')
        if len(lines) <= max_lines:
            return text
        
        # 返回开头和结尾的部分
        head = lines[:max_lines // 2]
        tail = lines[-max_lines // 2:]
        return '\n'.join(head) + '\n...\n' + '\n'.join(tail)
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重：相同文件和位置的代码块只保留一个"""
        seen = set()
        unique_results = []
        
        for result in results:
            file_path = result.get('file_path', '')
            start_line = result.get('start_line', 0)
            end_line = result.get('end_line', 0)
            
            # 使用文件路径和行号范围作为唯一标识
            key = f"{file_path}:{start_line}-{end_line}"
            
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results
    
    def search(
        self,
        information_request: str,
        project: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """
        执行代码库语义搜索

        流程：
        1. 使用向量检索获取候选代码片段
        2. 使用 Rerank 模型对候选结果重排序
        3. 返回高分结果
        """
        if not information_request or not information_request.strip():
            logger.warning("搜索请求为空")
            return "[错误] 搜索请求不能为空"

        # 快速检查代码目录是否存在或为空
        if not self.code_dir.exists():
            logger.debug(f"代码目录不存在: {self.code_dir}")
            return f"[提示] 代码目录不存在。请在 {self.code_dir} 目录下创建项目文件夹。"

        # 检查是否有项目
        project_dirs = [d for d in self.code_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if not project_dirs:
            logger.debug("代码库为空，未找到任何项目")
            return "[提示] 代码库中暂无项目。请在 workspace/code 目录下创建项目文件夹后再进行搜索。"

        # 延迟初始化
        self._lazy_init()

        if not self.indexer:
            return "[错误] 代码库索引管理器初始化失败"

        # 获取项目列表
        try:
            projects = self.indexer.get_project_list()
        except Exception as e:
            logger.error(f"获取项目列表失败: {type(e).__name__}: {e}")
            return f"[错误] 获取项目列表失败: {e}"

        if not projects:
            logger.info("代码库为空，未找到任何项目")
            return "[提示] 代码库中暂无项目。请在 workspace/code 目录下创建项目文件夹后再进行搜索。"

        # 如果指定了项目，检查是否存在
        if project and project not in projects:
            available = ', '.join(projects)
            logger.warning(f"指定项目不存在: {project}，可用项目: {available}")
            return f"[错误] 项目 '{project}' 不存在。可用项目: {available}"

        try:
            # Step 1: 向量检索 - 获取候选结果
            # 检索更多候选，给 Rerank 提供充分的选择
            retrieve_k = min(top_k * 4, 20)  # 最多检索20个候选

            logger.debug(f"开始向量检索: query='{information_request[:50]}...', 项目={project or '全部'}, retrieve_k={retrieve_k}")

            candidates = self.indexer.search(
                query=information_request,
                project=project,
                top_k=retrieve_k
            )

            if not candidates:
                logger.info(f"未找到相关代码: query='{information_request[:50]}...', 项目={project or '全部'}")
                if project:
                    return f"[结果] 在项目 '{project}' 中未找到与 '{information_request}' 相关的代码"
                else:
                    return f"[结果] 未找到与 '{information_request}' 相关的代码"

            logger.debug(f"向量检索返回 {len(candidates)} 个候选")

            # 去重
            candidates = self._deduplicate_results(candidates)
            logger.debug(f"去重后剩余 {len(candidates)} 个候选")

            # Step 2: Rerank 重排序
            # 如果候选数量较少，直接使用；否则使用 Reranker
            if len(candidates) <= top_k:
                final_results = candidates
                logger.debug(f"候选数量({len(candidates)}) <= top_k({top_k})，跳过 Rerank")
            else:
                logger.debug(f"开始 Rerank 重排序: {len(candidates)} 个候选 -> top {top_k}")

                reranked = self.reranker.rerank(
                    query=information_request,
                    documents=candidates,
                    top_k=top_k
                )

                final_results = reranked
                logger.info(f"代码搜索完成: query='{information_request[:50]}...', 返回 {len(final_results)} 个结果")

            # Step 3: 格式化输出
            return self._format_results(
                information_request,
                final_results,
                project,
                len(candidates)
            )

        except Exception as e:
            logger.error(f"搜索失败: {type(e).__name__}: {e}")
            return f"[错误] 搜索失败: {str(e)}"
    
    def _format_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        project: Optional[str],
        total_candidates: int
    ) -> str:
        """格式化搜索结果"""
        lines = []
        
        # 头部信息
        lines.append(f"🔍 搜索: {query}")
        if project:
            lines.append(f"📁 项目: {project}")
        lines.append(f"📊 从 {total_candidates} 个候选中精选 {len(results)} 个结果:\n")
        
        # 结果列表
        for i, result in enumerate(results, 1):
            file_path = result.get('file_path', 'unknown')
            project_name = result.get('project', 'unknown')
            chunk_type = result.get('chunk_type', '')
            chunk_name = result.get('chunk_name', '')
            start_line = result.get('start_line', 0)
            end_line = result.get('end_line', 0)
            
            # 分数信息
            vector_score = result.get('score', 0.0)
            rerank_score = result.get('rerank_score', None)
            
            # 标题行
            title = f"{i}. {project_name}/{file_path}"
            if chunk_name and chunk_name != 'module':
                title += f" [{chunk_type}:{chunk_name}]"
            title += f" (行{start_line}-{end_line})"
            lines.append(title)
            
            # 分数
            score_str = f"   向量相似度: {vector_score:.3f}"
            if rerank_score is not None:
                score_str += f" | Rerank: {rerank_score:.3f}"
            lines.append(score_str)
            
            # 代码片段
            code_text = result.get('text', '')
            if code_text:
                formatted_code = self._format_code_snippet(code_text, max_lines=12)
                lines.append("   ```")
                for code_line in formatted_code.split('\n'):
                    lines.append(f"   {code_line}")
                lines.append("   ```")
            
            lines.append("")  # 空行分隔
        
        # 底部提示
        lines.append("💡 提示: 使用 'project' 参数指定项目名可缩小搜索范围")
        
        return '\n'.join(lines)


# 全局工具实例缓存
_tool_instance: Optional[CodebaseSearchTool] = None


def get_search_tool(base_dir: Path) -> CodebaseSearchTool:
    """获取搜索工具实例"""
    global _tool_instance
    if _tool_instance is None:
        try:
            _tool_instance = CodebaseSearchTool(base_dir)
            logger.debug(f"搜索工具实例创建成功: {base_dir}")
        except Exception as e:
            logger.error(f"搜索工具实例创建失败: {type(e).__name__}: {e}")
            raise
    return _tool_instance


def create_search_codebase_tool(base_dir: Path) -> BaseTool:
    """创建代码库语义搜索工具"""
    tool = get_search_tool(base_dir)
    
    def search_func(
        information_request: str,
        project: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """代码库语义搜索入口函数"""
        return tool.search(
            information_request=information_request,
            project=project,
            top_k=top_k
        )
    
    code_dir = base_dir / "workspace" / "code"
    if code_dir.exists():
        project_dirs = [d.name for d in code_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        project_hint = f"可用项目: {', '.join(project_dirs)}" if project_dirs else "请在 workspace/code 下创建项目文件夹"
    else:
        project_hint = "请在 workspace/code 下创建项目文件夹"
    
    return StructuredTool.from_function(
        name="search_codebase",
        description=f"""语义搜索代码库 - 用自然语言描述查找相关代码。

【适用场景 - 模糊概念】
- 描述需求找代码（如"用户认证怎么实现"）
- 不知道具体函数名，只知道功能
- 理解代码语义，不依赖关键词
- 找与某功能相关的所有代码

【不适用场景 - 用 grep】
- 知道确切的函数名/变量名
- 需要精确匹配特定字符串
- 查找 TODO/FIXME 标记

【工作目录】 {base_dir / "workspace" / "code"}
【索引位置】 {base_dir / "storage" / "codebase_index"}

【参数】
- information_request (字符串, 必需): 自然语言描述
  示例: "用户登录认证逻辑"
  示例: "数据库连接代码"
  示例: "文件上传处理"

- project (字符串, 可选): 指定项目名称
  {project_hint}

- top_k (整数, 可选): 返回结果数量，默认5

【使用示例】
1. 搜索认证相关代码:
   information_request="用户登录认证逻辑"

2. 在指定项目搜索:
   information_request="数据库连接"
   project="my-backend"

【技术原理】
1. 向量检索: 将代码和查询转为向量，找语义相似候选
2. Rerank: 对候选结果重排序，提高准确性
3. 代码分块: 按函数/类索引，精准定位

【搜索工具选择】
┌─────────────────────┬─────────────────────┬─────────────────────────┐
│      场景           │     推荐工具        │         原因            │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ 模糊概念/语义       │ search_codebase    │ 理解意图，智能搜索      │
│ 知道函数/变量名     │ grep               │ 精确匹配，快速定位      │
│ 找某类型文件        │ glob               │ 按文件名模式匹配        │
│ 浏览目录结构        │ list_workspace     │ 目录树展示              │
└─────────────────────┴─────────────────────┴─────────────────────────┘
""",
        func=search_func,
        args_schema=SearchCodebaseInput
    )


def build_all_codebase_indexes(base_dir: Path) -> Dict[str, bool]:
    """
    构建所有项目的代码库索引
    可在应用启动时调用
    """
    try:
        indexer = get_codebase_indexer(base_dir)
        logger.debug(f"开始构建所有项目代码库索引: {base_dir}")
        results = indexer.build_all_indexes()
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"代码库索引构建完成: 成功 {success_count}/{len(results)} 个项目")
        return results
    except Exception as e:
        logger.error(f"构建代码库索引失败: {type(e).__name__}: {e}")
        raise
