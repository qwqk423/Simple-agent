"""Grep 精确搜索工具 - 基于 ripgrep 的模式匹配，适合已知具体代码片段"""
import subprocess
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool


class GrepInput(BaseModel):
    """Grep 工具的输入参数"""
    pattern: str = Field(description="要搜索的正则表达式模式（如 'def authenticate', 'class.*View', 'TODO'）")
    path: Optional[str] = Field(default=None, description="搜索的目录或文件路径（相对于工作目录）")
    glob: Optional[str] = Field(default=None, description="用于过滤文件的glob模式（如 '*.py', '**/*.ts'）")
    output_mode: str = Field(default="content", description="输出模式: content(显示内容) / files_with_matches(仅显示文件) / count(计数)")
    case_sensitive: bool = Field(default=True, description="是否区分大小写，默认为true")
    show_line_numbers: bool = Field(default=True, description="在输出中显示行号，默认为true")
    after_context: Optional[int] = Field(default=None, description="显示每个匹配之后的行数（rg -A）")
    before_context: Optional[int] = Field(default=None, description="显示每个匹配之前的行数（rg -B）")
    context: Optional[int] = Field(default=None, description="显示每个匹配之前和之后的行数（rg -C）")
    head_limit: Optional[int] = Field(default=None, description="限制输出结果数量")
    multiline: bool = Field(default=False, description="启用多行模式（rg -U）")


def is_safe_path(root_dir: Path, target_path: Optional[str]) -> tuple[bool, Optional[str]]:
    """安全检查"""
    if not target_path:
        return True, None
    
    try:
        target = (root_dir / target_path).resolve()
        target.relative_to(root_dir)
    except ValueError:
        return False, "路径逃逸检测: 禁止访问项目目录外的文件"
    
    if ".." in target_path or "~" in target_path:
        return False, "路径包含非法字符"
    
    return True, None


def build_ripgrep_args(
    pattern: str,
    search_path: Path,
    glob: Optional[str] = None,
    case_sensitive: bool = True,
    show_line_numbers: bool = True,
    after_context: Optional[int] = None,
    before_context: Optional[int] = None,
    context: Optional[int] = None,
    multiline: bool = False
) -> List[str]:
    """构建 ripgrep 命令参数"""
    args = ["rg", pattern]
    
    # 输出模式
    args.extend(["--color", "never"])
    
    # 大小写敏感
    if not case_sensitive:
        args.append("-i")
    
    # 显示行号
    if show_line_numbers:
        args.append("-n")
    
    # 上下文行
    if context is not None:
        args.extend(["-C", str(context)])
    else:
        if after_context is not None:
            args.extend(["-A", str(after_context)])
        if before_context is not None:
            args.extend(["-B", str(before_context)])
    
    # 多行模式
    if multiline:
        args.append("-U")
    
    # glob 过滤
    if glob:
        args.extend(["--glob", glob])
    
    # 搜索路径
    args.append(str(search_path))
    
    return args


def grep_search(
    root_dir: Path,
    pattern: str,
    path: Optional[str] = None,
    glob: Optional[str] = None,
    output_mode: str = "content",
    case_sensitive: bool = True,
    show_line_numbers: bool = True,
    after_context: Optional[int] = None,
    before_context: Optional[int] = None,
    context: Optional[int] = None,
    head_limit: Optional[int] = None,
    multiline: bool = False
) -> str:
    """执行 grep 搜索"""
    # 安全检查
    safe, msg = is_safe_path(root_dir, path)
    if not safe:
        return f"[安全拦截] {msg}"
    
    # 确定搜索路径
    if path:
        search_path = (root_dir / path).resolve()
    else:
        search_path = root_dir
    
    # 检查路径是否存在
    if not search_path.exists():
        return f"[错误] 路径不存在: {path or '.'}"
    
    try:
        # 构建命令
        if output_mode == "files_with_matches":
            # 仅显示匹配的文件
            cmd = ["rg", "-l", "--color", "never"]
            if not case_sensitive:
                cmd.append("-i")
            if glob:
                cmd.extend(["--glob", glob])
            cmd.extend([pattern, str(search_path)])
        elif output_mode == "count":
            # 统计匹配数
            cmd = ["rg", "-c", "--color", "never"]
            if not case_sensitive:
                cmd.append("-i")
            if glob:
                cmd.extend(["--glob", glob])
            cmd.extend([pattern, str(search_path)])
        else:
            # 默认：显示内容
            cmd = build_ripgrep_args(
                pattern=pattern,
                search_path=search_path,
                glob=glob,
                case_sensitive=case_sensitive,
                show_line_numbers=show_line_numbers,
                after_context=after_context,
                before_context=before_context,
                context=context,
                multiline=multiline
            )
        
        # 执行搜索
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        # 处理结果
        if result.returncode == 0:
            output = result.stdout
        elif result.returncode == 1:
            # 没有找到匹配
            return f"[结果] 未找到匹配 '{pattern}' 的内容"
        else:
            return f"[错误] 搜索失败: {result.stderr}"
        
        # 限制输出数量
        if head_limit and output:
            lines = output.split("\n")
            if len(lines) > head_limit:
                output = "\n".join(lines[:head_limit]) + f"\n\n...[已截断，仅显示前 {head_limit} 行]"
        
        if not output.strip():
            return f"[结果] 未找到匹配 '{pattern}' 的内容"
        
        return output
        
    except FileNotFoundError:
        return "[错误] 未找到 ripgrep (rg) 命令，请安装 ripgrep: https://github.com/BurntSushi/ripgrep"
    except Exception as e:
        return f"[错误] 搜索失败: {str(e)}"


def create_grep_tool(base_dir: Path) -> BaseTool:
    """创建 Grep 精确搜索工具"""
    root_dir = (base_dir / "workspace").resolve()
    
    def grep_func(
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        output_mode: str = "content",
        case_sensitive: bool = True,
        show_line_numbers: bool = True,
        after_context: Optional[int] = None,
        before_context: Optional[int] = None,
        context: Optional[int] = None,
        head_limit: Optional[int] = None,
        multiline: bool = False
    ) -> str:
        """Grep 搜索入口函数"""
        if not pattern:
            return "[错误] pattern 不能为空"
        
        return grep_search(
            root_dir=root_dir,
            pattern=pattern,
            path=path,
            glob=glob,
            output_mode=output_mode,
            case_sensitive=case_sensitive,
            show_line_numbers=show_line_numbers,
            after_context=after_context,
            before_context=before_context,
            context=context,
            head_limit=head_limit,
            multiline=multiline
        )
    
    return StructuredTool.from_function(
        name="grep",
        description=f"""精确模式搜索工具 - 基于正则表达式查找代码。

【适用场景 - 知道具体代码】
- 查找特定函数定义（如知道函数名）
- 搜索特定类名、变量名
- 查找 TODO/FIXME 标记
- 搜索特定字符串模式
- 验证某个代码模式是否存在

【不适用场景 - 用 search_codebase】
- 模糊概念搜索（如"用户认证逻辑"）
- 不知道具体代码内容
- 需要理解代码语义

【工作目录】 {base_dir / "workspace"}

【参数】
- pattern (字符串, 必需): 正则表达式模式
  示例: "def authenticate"      # 查找函数定义
  示例: "class.*View"           # 查找 View 类
  示例: "TODO|FIXME"            # 查找 TODO/FIXME
  示例: "import\\s+requests"    # 查找导入语句

- path (字符串, 可选): 搜索路径（相对路径）
- glob (字符串, 可选): 文件过滤，如 "*.py"
- output_mode (字符串, 可选): content(默认) / files_with_matches / count
- context (整数, 可选): 显示匹配前后 N 行
- head_limit (整数, 可选): 限制结果数量
- case_sensitive (布尔, 可选): 是否区分大小写，默认 true

【常用选项】
1. 忽略大小写搜索:
   pattern="hello"
   case_sensitive=false
   # 可匹配: hello, Hello, HELLO

2. 只搜索特定文件类型:
   pattern="def "
   glob="*.py"

3. 显示匹配上下文:
   pattern="TODO"
   context=2  # 显示匹配前后2行

4. 限制结果数量:
   pattern="import"
   head_limit=20

【使用示例】
1. 查找所有认证相关函数:
   pattern="def.*auth"
   glob="*.py"

2. 查找 API 调用位置（带上下文）:
   pattern="api\\.example\\.com"
   context=3

3. 忽略大小写查找配置项:
   pattern="debug=true"
   case_sensitive=false
   glob="*.conf"

【搜索工具选择】
┌─────────────────────┬─────────────────────┬─────────────────────────┐
│      场景           │     推荐工具        │         原因            │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ 知道函数/变量名     │ grep               │ 精确匹配，快速定位      │
│ 模糊概念/语义       │ search_codebase    │ 理解意图，智能搜索      │
│ 找某类型文件        │ glob               │ 按文件名模式匹配        │
│ 浏览目录结构        │ list_workspace     │ 目录树展示              │
└─────────────────────┴─────────────────────┴─────────────────────────┘
""",
        func=grep_func,
        args_schema=GrepInput
    )
