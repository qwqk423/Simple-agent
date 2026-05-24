"""会话标题生成器 - 统一处理标题生成逻辑"""
import asyncio

from utils.llm_factory import create_llm
from utils.logger import get_logger

logger = get_logger("TitleGenerator")

# 常量定义
TITLE_MAX_LENGTH = 10  # 标题最大长度限制，与提示词中的"不超过10个中文字符"保持一致
TITLE_TEMPERATURE = 0.3  # 生成标题时的温度参数
TITLE_GENERATION_TIMEOUT = 30  # 标题生成超时时间（秒）


class TitleGenerator:
    """会话标题生成器"""
    
    DEFAULT_TITLE = "新对话"
    TITLE_PROMPT_TEMPLATE = """请为以下对话生成一个简短的标题（不超过10个中文字符）。
只返回标题文本，不要有任何解释或标点。

用户消息: %s

标题:"""
    
    def __init__(self):
        # 不在这里创建 LLM 实例，每次调用时动态创建以获取最新配置
        self._temperature = TITLE_TEMPERATURE
    
    async def generate(self, message: str) -> str:
        """
        根据用户消息生成标题

        Args:
            message: 用户的第一条消息

        Returns:
            生成的标题字符串，失败时返回默认标题
        """
        if not message or not message.strip():
            logger.debug("消息为空，使用默认标题")
            return self.DEFAULT_TITLE

        try:
            # 动态创建 LLM 以获取最新配置，标题生成不需要思考模式
            llm = create_llm(temperature=self._temperature, override_params={"thinking_enabled": False})
            # 使用 % 格式化避免用户消息中的特殊字符（如 {}）导致 format 错误
            prompt = self.TITLE_PROMPT_TEMPLATE % message.strip()

            logger.debug(f"开始生成标题，消息长度={len(message)}")
            # 添加超时控制，防止长时间挂起
            response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=TITLE_GENERATION_TIMEOUT)

            # 检查响应是否有效
            if not response or not hasattr(response, 'content'):
                logger.warning(f"LLM响应无效，使用默认标题")
                return self.DEFAULT_TITLE

            raw_title = response.content.strip()
            logger.debug(f"LLM返回原始标题: '{raw_title}'")

            # 清理标题
            title = self._clean_title(raw_title)

            logger.info(f"标题生成成功: '{title}' (原始长度={len(raw_title)})")
            return title

        except TimeoutError as e:
            logger.error(f"生成标题超时: {e}")
            return self.DEFAULT_TITLE
        except ConnectionError as e:
            logger.error(f"生成标题时连接失败: {e}")
            return self.DEFAULT_TITLE
        except Exception as e:
            logger.error(f"生成标题失败: {type(e).__name__}: {e}")
            return self.DEFAULT_TITLE
    
    def _clean_title(self, title: str) -> str:
        """清理和截断标题"""
        if not title:
            logger.debug("清理标题时发现空值，返回默认标题")
            return self.DEFAULT_TITLE

        original_len = len(title)

        # 移除引号
        title = title.replace('"', '').replace("'", "").strip()

        # 如果清理后为空
        if not title:
            logger.debug("清理后标题为空，使用默认标题")
            return self.DEFAULT_TITLE

        # 截断至最大长度
        if len(title) > TITLE_MAX_LENGTH:
            title = title[:TITLE_MAX_LENGTH]
            logger.debug(f"标题截断: {original_len} -> {len(title)} 字符")

        return title


# 全局标题生成器实例
try:
    title_generator = TitleGenerator()
    logger.debug("TitleGenerator 全局实例创建成功")
except Exception as e:
    logger.error(f"TitleGenerator 全局实例创建失败: {e}")
    raise
