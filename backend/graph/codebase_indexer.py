"""代码库向量索引器 - 为 workspace/code 下的项目构建向量索引"""
import hashlib
import json
import os
import re
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from llama_index.core import VectorStoreIndex, Document, StorageContext, load_index_from_storage
from llama_index.core.node_parser import CodeSplitter

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import settings
from utils.embedding_adapter import create_openai_embedding
from utils.logger import get_logger

logger = get_logger("CodebaseIndexer")


# 支持的代码文件扩展名
CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r',
    '.m', '.mm', '.sql', '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
    '.html', '.htm', '.xml', '.json', '.yaml', '.yml', '.toml', '.ini',
    '.cfg', '.conf', '.config', '.md', '.rst', '.txt', '.css', '.scss',
    '.sass', '.less', '.vue', '.svelte'
}

# 忽略的文件和目录
IGNORE_PATTERNS = {
    'node_modules', '.git', '__pycache__', 'venv', '.venv', '.env',
    'dist', 'build', '.idea', '.vscode', '.pytest_cache', '.mypy_cache',
    '.ruff_cache', '.tox', '.eggs', '*.egg-info', 'target', 'out',
    '.next', '.nuxt', 'coverage', '.coverage', 'htmlcov'
}


class CodebaseProjectIndexer:
    """单个项目的代码库索引器"""
    
    def __init__(self, base_dir: Path, project_name: str):
        self.base_dir = base_dir
        self.project_name = project_name
        self.project_path = base_dir / "workspace" / "code" / project_name
        self.storage_dir = base_dir / "storage" / "codebase_index" / project_name
        self.metadata_file = self.storage_dir / "index_meta.json"
        
        self.index: Optional[VectorStoreIndex] = None
        self.file_hashes: Dict[str, str] = {}
        
        # 线程锁
        self._lock = threading.Lock()
        
        # Embedding 模型（模型名称从 settings.EMBEDDING_MODEL 自动读取）
        # 优先使用独立的 EMBEDDING_API_KEY 和 EMBEDDING_BASE_URL
        embed_api_key = settings.embedding_api_key if settings.embedding_api_key else settings.openai_api_key
        embed_base_url = settings.embedding_base_url if settings.embedding_base_url else settings.openai_base_url
        self.embed_model = create_openai_embedding(
            api_key=embed_api_key,
            base_url=embed_base_url
        )
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件 MD5"""
        try:
            content = file_path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    def _is_code_file(self, file_path: Path) -> bool:
        """检查是否为代码文件"""
        return file_path.suffix.lower() in CODE_EXTENSIONS
    
    def _should_ignore(self, path: Path) -> bool:
        """检查路径是否应该被忽略"""
        path_str = str(path)
        for pattern in IGNORE_PATTERNS:
            if pattern.startswith('*'):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str.split(os.sep):
                return True
        return False
    
    def _extract_code_structure(self, content: str, file_ext: str) -> List[Dict[str, Any]]:
        """
        提取代码结构信息（函数、类等）
        返回代码块的列表
        """
        chunks = []
        
        if file_ext == '.py':
            chunks = self._parse_python_code(content)
        elif file_ext in ['.js', '.ts', '.jsx', '.tsx']:
            chunks = self._parse_javascript_code(content)
        elif file_ext == '.java':
            chunks = self._parse_java_code(content)
        else:
            # 通用分块：按段落/空行分割
            chunks = self._generic_chunking(content)
        
        return chunks
    
    def _parse_python_code(self, content: str) -> List[Dict[str, Any]]:
        """解析 Python 代码，提取函数和类
        
        Note: 使用简单正则解析，对于复杂嵌套结构（如嵌套类、装饰器等）可能处理不完美。
        考虑使用 ast 模块进行更健壮的解析。
        """
        chunks = []
        lines = content.split('\n')
        
        # 正则匹配函数和类定义
        # TODO: 对于复杂嵌套结构（如嵌套函数、多行装饰器等），建议使用 Python ast 模块
        pattern = re.compile(r'^(\s*)(def|class)\s+(\w+)\s*[\(:]')
        
        current_chunk = None
        current_lines = []
        current_indent = 0
        
        for i, line in enumerate(lines):
            match = pattern.match(line)
            
            if match:
                # 保存之前的 chunk
                if current_chunk and current_lines:
                    current_chunk['content'] = '\n'.join(current_lines)
                    current_chunk['end_line'] = i
                    chunks.append(current_chunk)
                
                indent = len(match.group(1))
                chunk_type = match.group(2)  # def 或 class
                name = match.group(3)
                
                current_chunk = {
                    'type': chunk_type,
                    'name': name,
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'content': '',
                    'indent': indent
                }
                current_lines = [line]
                current_indent = indent
            elif current_chunk is not None:
                # 检查是否退出当前代码块（缩进小于等于定义行的缩进，且不是空行）
                if line.strip():
                    line_indent = len(line) - len(line.lstrip())
                    if line_indent <= current_indent and not line.strip().startswith('#'):
                        # 保存当前 chunk
                        current_chunk['content'] = '\n'.join(current_lines)
                        current_chunk['end_line'] = i
                        chunks.append(current_chunk)
                        current_chunk = None
                        current_lines = []
                    else:
                        current_lines.append(line)
                else:
                    current_lines.append(line)
        
        # 处理最后一个 chunk
        if current_chunk and current_lines:
            current_chunk['content'] = '\n'.join(current_lines)
            current_chunk['end_line'] = len(lines)
            chunks.append(current_chunk)
        
        # 如果没有解析到任何 chunk，将整个文件作为一个 chunk
        if not chunks:
            chunks.append({
                'type': 'file',
                'name': 'module',
                'start_line': 1,
                'end_line': len(lines),
                'content': content,
                'indent': 0
            })
        
        return chunks
    
    def _parse_javascript_code(self, content: str) -> List[Dict[str, Any]]:
        """解析 JavaScript/TypeScript 代码
        
        Note: 使用简单正则和花括号计数，对于复杂嵌套结构（如模板字符串内的花括号、
        正则表达式字面量等）可能处理不完美。
        """
        chunks = []
        lines = content.split('\n')
        
        # 匹配函数定义、类定义、箭头函数等
        # TODO: 对于复杂的 JS/TS 特性（如 JSX、嵌套模板字符串等），建议使用专门的解析器
        patterns = [
            (re.compile(r'^(\s*)(function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*(?:async\s*)?\(|(\w+)\s*=\s*(?:async\s*)?\s*\('), 'function'),
            (re.compile(r'^(\s*)(class)\s+(\w+)'), 'class'),
            (re.compile(r'^(\s*)(const|let|var)\s+(\w+)\s*='), 'variable'),
        ]
        
        current_chunk = None
        current_lines = []
        brace_count = 0
        in_chunk = False
        
        for i, line in enumerate(lines):
            matched = False
            
            if not in_chunk:
                for pattern, chunk_type in patterns:
                    match = pattern.match(line)
                    if match:
                        if current_chunk and current_lines:
                            current_chunk['content'] = '\n'.join(current_lines)
                            current_chunk['end_line'] = i
                            chunks.append(current_chunk)
                        
                        name = match.group(3) or match.group(4) or match.group(5) or match.group(6) or 'anonymous'
                        current_chunk = {
                            'type': chunk_type,
                            'name': name,
                            'start_line': i + 1,
                            'end_line': i + 1,
                            'content': '',
                            'indent': len(match.group(1))
                        }
                        current_lines = [line]
                        brace_count = line.count('{') - line.count('}')
                        in_chunk = True
                        matched = True
                        break
            else:
                current_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                
                # 简单判断代码块结束（花括号平衡）
                if brace_count <= 0 and '{' in ''.join(current_lines):
                    current_chunk['content'] = '\n'.join(current_lines)
                    current_chunk['end_line'] = i + 1
                    chunks.append(current_chunk)
                    current_chunk = None
                    current_lines = []
                    brace_count = 0
                    in_chunk = False
        
        if current_chunk and current_lines:
            current_chunk['content'] = '\n'.join(current_lines)
            current_chunk['end_line'] = len(lines)
            chunks.append(current_chunk)
        
        if not chunks:
            chunks.append({
                'type': 'file',
                'name': 'module',
                'start_line': 1,
                'end_line': len(lines),
                'content': content,
                'indent': 0
            })
        
        return chunks
    
    def _parse_java_code(self, content: str) -> List[Dict[str, Any]]:
        """解析 Java 代码
        
        Note: 当前复用 JS 解析逻辑，但 Java 有泛型、注解等特性，
        建议使用专门的 Java 解析器（如 javalang）进行更准确的解析。
        """
        # TODO: 对于复杂的 Java 特性（如泛型、注解、内部类等），建议使用 javalang 等库
        return self._parse_javascript_code(content)
    
    def _generic_chunking(self, content: str, max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """通用分块策略"""
        chunks = []
        lines = content.split('\n')
        
        current_chunk_lines = []
        current_size = 0
        chunk_start = 1
        
        for i, line in enumerate(lines):
            line_size = len(line)
            
            if current_size + line_size > max_chunk_size and current_chunk_lines:
                chunks.append({
                    'type': 'chunk',
                    'name': f'chunk_{len(chunks)}',
                    'start_line': chunk_start,
                    'end_line': i,
                    'content': '\n'.join(current_chunk_lines),
                    'indent': 0
                })
                current_chunk_lines = []
                current_size = 0
                chunk_start = i + 1
            
            current_chunk_lines.append(line)
            current_size += line_size + 1  # +1 for newline
        
        if current_chunk_lines:
            chunks.append({
                'type': 'chunk',
                'name': f'chunk_{len(chunks)}',
                'start_line': chunk_start,
                'end_line': len(lines),
                'content': '\n'.join(current_chunk_lines),
                'indent': 0
            })
        
        return chunks
    
    def _scan_project_files(self) -> List[Path]:
        """扫描项目中的所有代码文件"""
        code_files = []
        
        if not self.project_path.exists():
            return code_files
        
        for root, dirs, files in os.walk(self.project_path):
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if not self._should_ignore(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                if self._is_code_file(file_path) and not self._should_ignore(file_path):
                    # 跳过过大的文件 (>100KB)
                    try:
                        if file_path.stat().st_size > 100 * 1024:
                            continue
                    except Exception:
                        continue
                    code_files.append(file_path)
        
        return code_files
    
    def _load_metadata(self) -> Dict[str, Any]:
        """加载索引元数据"""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[{self.project_name}] 加载元数据失败: {e}")
            return {}
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """保存索引元数据"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[{self.project_name}] 保存元数据失败: {e}")
    
    def _get_file_relative_path(self, file_path: Path) -> str:
        """获取相对于项目根目录的文件路径"""
        try:
            return str(file_path.relative_to(self.project_path))
        except Exception:
            return str(file_path)
    
    def rebuild_index(self) -> bool:
        """重建项目索引"""
        with self._lock:
            if not self.project_path.exists():
                logger.warning(f"[{self.project_name}] 项目不存在: {self.project_path}")
                return False
            
            try:
                # 扫描所有代码文件
                code_files = self._scan_project_files()
                logger.info(f"[{self.project_name}] 发现 {len(code_files)} 个代码文件")
                
                if not code_files:
                    logger.warning(f"[{self.project_name}] 没有找到代码文件")
                    return False
                
                # 创建文档
                documents = []
                file_hashes = {}
                
                for file_path in code_files:
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        file_hash = self._calculate_file_hash(file_path)
                        relative_path = self._get_file_relative_path(file_path)
                        
                        file_hashes[relative_path] = file_hash
                        
                        # 提取代码结构
                        chunks = self._extract_code_structure(content, file_path.suffix.lower())
                        
                        for chunk in chunks:
                            doc = Document(
                                text=chunk['content'],
                                metadata={
                                    'file_path': relative_path,
                                    'project': self.project_name,
                                    'chunk_type': chunk['type'],
                                    'chunk_name': chunk['name'],
                                    'start_line': chunk['start_line'],
                                    'end_line': chunk['end_line'],
                                    'file_hash': file_hash
                                }
                            )
                            documents.append(doc)
                        
                    except Exception as e:
                        logger.warning(f"[{self.project_name}] 处理文件失败 {file_path}: {e}")
                        continue
                
                if not documents:
                    logger.warning(f"[{self.project_name}] 没有可索引的内容")
                    return False
                
                # 构建向量索引
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    embed_model=self.embed_model
                )
                
                # 持久化索引
                self.storage_dir.mkdir(parents=True, exist_ok=True)
                self.index.storage_context.persist(str(self.storage_dir))
                
                # 保存元数据
                metadata = {
                    'project_name': self.project_name,
                    'file_hashes': file_hashes,
                    'document_count': len(documents),
                    'file_count': len(code_files),
                    'updated_at': datetime.now().isoformat()
                }
                self._save_metadata(metadata)
                self.file_hashes = file_hashes
                
                logger.info(f"[{self.project_name}] 索引重建成功: {len(documents)} 个文档片段, {len(code_files)} 个文件")
                return True
                
            except Exception as e:
                logger.error(f"[{self.project_name}] 索引重建失败: {e}")
                return False
    
    def check_and_update(self) -> bool:
        """检查文件变更并增量更新"""
        with self._lock:
            if not self.project_path.exists():
                return False
            
            metadata = self._load_metadata()
            stored_hashes = metadata.get('file_hashes', {})
            
            # 扫描当前文件
            current_files = self._scan_project_files()
            current_paths = {self._get_file_relative_path(f) for f in current_files}
            
            # 检测变更
            changed_files = []
            new_files = []
            deleted_files = set(stored_hashes.keys()) - current_paths
            
            for file_path in current_files:
                relative_path = self._get_file_relative_path(file_path)
                current_hash = self._calculate_file_hash(file_path)
                
                if relative_path not in stored_hashes:
                    new_files.append(file_path)
                elif stored_hashes[relative_path] != current_hash:
                    changed_files.append(file_path)
            
            # 如果有变更，重建索引
            if changed_files or new_files or deleted_files:
                logger.info(f"[{self.project_name}] 检测到文件变更: 新增={len(new_files)}, 修改={len(changed_files)}, 删除={len(deleted_files)}")
                # 为了简单起见，直接重建索引
                # 更复杂的场景可以实现真正的增量更新
                return self.rebuild_index()
            
            return True
    
    def load_index(self) -> bool:
        """加载已有索引"""
        with self._lock:
            if not self.storage_dir.exists():
                return False
            
            try:
                storage_context = StorageContext.from_defaults(persist_dir=str(self.storage_dir))
                self.index = load_index_from_storage(
                    storage_context,
                    embed_model=self.embed_model
                )
                
                # 加载元数据
                metadata = self._load_metadata()
                self.file_hashes = metadata.get('file_hashes', {})
                
                logger.info(f"[{self.project_name}] 索引加载成功")
                return True
                
            except Exception as e:
                logger.error(f"[{self.project_name}] 索引加载失败: {e}")
                return False
    
    def ensure_index(self) -> bool:
        """确保索引可用"""
        # 先尝试加载
        if self.load_index():
            # 检查是否需要更新
            return self.check_and_update()
        
        # 重建索引
        return self.rebuild_index()
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """检索代码"""
        if not self.ensure_index():
            return []
        
        try:
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)
            
            results = []
            seen = set()
            
            for node in nodes:
                file_path = node.node.metadata.get('file_path', '')
                chunk_name = node.node.metadata.get('chunk_name', '')
                
                # 去重：相同文件和代码块的只保留一次
                key = f"{file_path}:{chunk_name}"
                if key in seen:
                    continue
                seen.add(key)
                
                results.append({
                    'text': node.node.text,
                    'score': float(node.score) if hasattr(node, 'score') else 0.0,
                    'file_path': file_path,
                    'project': self.project_name,
                    'chunk_type': node.node.metadata.get('chunk_type', ''),
                    'chunk_name': node.node.metadata.get('chunk_name', ''),
                    'start_line': node.node.metadata.get('start_line', 0),
                    'end_line': node.node.metadata.get('end_line', 0),
                    'source': f"{self.project_name}/{file_path}"
                })
            
            return results
            
        except Exception as e:
            logger.error(f"[{self.project_name}] 检索失败: {e}")
            return []


class CodebaseIndexerManager:
    """代码库索引管理器 - 管理多个项目的索引"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.code_dir = base_dir / "workspace" / "code"
        self.indexers: Dict[str, CodebaseProjectIndexer] = {}
        self._lock = threading.Lock()
    
    def _get_project_names(self) -> List[str]:
        """获取所有项目名称"""
        if not self.code_dir.exists():
            return []
        
        projects = []
        for item in self.code_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                projects.append(item.name)
        
        return projects
    
    def _get_or_create_indexer(self, project_name: str) -> CodebaseProjectIndexer:
        """获取或创建项目索引器"""
        with self._lock:
            if project_name not in self.indexers:
                self.indexers[project_name] = CodebaseProjectIndexer(self.base_dir, project_name)
            return self.indexers[project_name]
    
    def build_all_indexes(self) -> Dict[str, bool]:
        """为所有项目构建索引"""
        projects = self._get_project_names()
        results = {}
        
        logger.info(f"发现 {len(projects)} 个项目: {projects}")
        
        for project in projects:
            indexer = self._get_or_create_indexer(project)
            results[project] = indexer.rebuild_index()
        
        return results
    
    def search(
        self,
        query: str,
        project: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索代码库
        
        Args:
            query: 搜索查询
            project: 指定项目名称，None 则搜索所有项目
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        results = []
        
        if project:
            # 搜索指定项目
            indexer = self._get_or_create_indexer(project)
            results = indexer.retrieve(query, top_k=top_k)
        else:
            # 搜索所有项目
            projects = self._get_project_names()
            per_project_k = max(1, top_k // len(projects)) if projects else top_k
            
            for proj in projects:
                try:
                    indexer = self._get_or_create_indexer(proj)
                    proj_results = indexer.retrieve(query, top_k=per_project_k * 2)
                    results.extend(proj_results)
                except Exception as e:
                    logger.warning(f"搜索项目 {proj} 失败: {e}")
                    continue
            
            # 按分数排序
            results.sort(key=lambda x: x['score'], reverse=True)
            results = results[:top_k]
        
        return results
    
    def get_project_list(self) -> List[str]:
        """获取项目列表"""
        return self._get_project_names()


# 全局管理器实例
_manager: Optional[CodebaseIndexerManager] = None


def get_codebase_indexer(base_dir: Path) -> CodebaseIndexerManager:
    """获取代码库索引管理器实例"""
    global _manager
    if _manager is None:
        _manager = CodebaseIndexerManager(base_dir)
    return _manager
