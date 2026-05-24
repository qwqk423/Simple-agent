"""Fetch 网络信息获取工具"""
import re
import json
import html2text
import requests
import urllib3
from typing import Optional, Union, Dict, Any
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from utils.logger import get_logger

logger = get_logger("FetchUrlTool")

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_url_content(url: str) -> str:
    """获取 URL 内容并转换为 Markdown"""
    # 添加 http:// 前缀（如果没有）
    original_url = url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        logger.debug(f"URL 自动添加 https 前缀: {original_url} -> {url}")

    logger.debug(f"开始获取 URL: {url}")

    try:
        # 发送请求（禁用 SSL 验证以解决证书问题）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()

        content = response.text
        content_type = response.headers.get('Content-Type', 'unknown')
        logger.debug(f"URL 请求成功: {url}, status={response.status_code}, content_type={content_type}, size={len(content)}")

        # 判断内容类型
        if _is_json(content):
            # JSON 格式化
            try:
                data = json.loads(content)
                result = json.dumps(data, ensure_ascii=False, indent=2)
                logger.debug(f"内容类型: JSON, 格式化后大小={len(result)}")
            except json.JSONDecodeError as e:
                # 内容看起来像 JSON 但解析失败，返回原始内容
                logger.warning(f"JSON 解析失败: {e}")
                result = content
        else:
            # HTML 转 Markdown
            result = _clean_html(content)

        # 截断输出
        if len(result) > 5000:
            logger.debug(f"内容截断: {len(result)} -> 5000 字符")
            result = result[:5000] + "\n\n...[内容已截断]"

        logger.info(f"URL 内容获取成功: {url}, 最终大小={len(result)}")
        return result

    except requests.Timeout:
        logger.error(f"URL 请求超时 (15s): {url}")
        return "[错误] 请求超时 (15s)"
    except requests.ConnectionError as e:
        logger.error(f"URL 连接失败: {url}, {e}")
        return f"[错误] 连接失败: {str(e)}"
    except requests.HTTPError as e:
        logger.error(f"URL HTTP 错误: {url}, status={e.response.status_code if e.response else 'unknown'}")
        return f"[错误] HTTP {e.response.status_code if e.response else 'unknown'}: {str(e)}"
    except requests.RequestException as e:
        logger.error(f"URL 请求失败: {url}, {type(e).__name__}: {e}")
        return f"[错误] 请求失败: {str(e)}"
    except Exception as e:
        logger.error(f"URL 获取失败: {url}, {type(e).__name__}: {e}")
        return f"[错误] {str(e)}"


def _is_json(text: str) -> bool:
    """检查是否为 JSON"""
    text = text.strip()
    return text.startswith("{") or text.startswith("[")


def _clean_html(html: str) -> str:
    """清理 HTML 并转换为 Markdown"""
    try:
        # 使用 BeautifulSoup 预处理
        soup = BeautifulSoup(html, "html.parser")

        # 移除脚本和样式
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # 使用 html2text 转换
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_tables = False
        h.body_width = 0  # 不自动换行

        markdown = h.handle(str(soup))

        # 清理多余空行
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        logger.debug(f"HTML 转 Markdown 成功: 原始大小={len(html)}, 转换后大小={len(markdown)}")
        return markdown.strip()
    except Exception as e:
        logger.error(f"HTML 解析失败: {type(e).__name__}: {e}")
        return f"[错误] HTML解析失败: {str(e)}"


class FetchUrlInput(BaseModel):
    """Fetch URL 工具的输入参数"""
    url: str = Field(description="要获取的 URL，如 'https://example.com/docs'")

def create_fetch_url_tool() -> BaseTool:
    """创建 Fetch URL 工具"""

    def fetch_func(url: str) -> str:
        """获取指定 URL 的网页内容"""
        if not url or not url.strip():
            logger.warning("URL 为空")
            return "[错误] URL 不能为空"

        logger.debug(f"Fetch URL 工具调用: {url}")
        return fetch_url_content(url)
    
    return StructuredTool.from_function(
        name="fetch_url",
        description="""获取 URL 内容 - 网页抓取、API 调用。

【适用场景】
- 获取网页内容（HTML 自动转 Markdown）
- 调用 REST API（JSON 格式化输出）
- 获取在线文档或资源

【参数】
- url (字符串, 必需): 要获取的 URL
  示例: "https://example.com/docs"
  示例: "api.example.com/v1/data"

【限制】
- 15秒超时
- 输出最多5000字符

【输出】
- HTML 自动转换为 Markdown
- JSON 格式化显示
""",
        func=fetch_func,
        args_schema=FetchUrlInput
    )
