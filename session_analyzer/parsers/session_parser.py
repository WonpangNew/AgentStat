"""
Session文件解析器
"""
import json
from typing import Iterator, Optional
from datetime import datetime
from loguru import logger

from ..models.message import Message, MessageType
from ..config import Config
from .content_parser import ContentParser


class SessionParser:
    """Session JSONL文件解析器"""

    def __init__(self, config: Config):
        self.config = config
        self.content_parser = ContentParser()

    def parse_session(self, file_path: str) -> Iterator[Message]:
        """
        流式解析session文件

        Args:
            file_path: JSONL文件路径

        Yields:
            Message对象
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    message = self._parse_message(data)
                    if message:
                        yield message
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析错误 (行 {line_num}): {e}")
                    continue
                except Exception as e:
                    logger.error(f"消息解析错误 (行 {line_num}): {e}")
                    continue

    def _parse_message(self, data: dict) -> Optional[Message]:
        """
        解析单条消息

        Args:
            data: JSON数据

        Returns:
            Message对象，如果解析失败返回None
        """
        try:
            # 提取基础字段
            message_id = data.get("messageId")
            session_id = data.get("sessionId", 0)
            role = data.get("role", "")
            content_str = data.get("content", "[]")
            user_origin_query = data.get("userOriginQuery", "")
            create_time_str = data.get("createTime")
            user_name = data.get("name", "")

            # 解析创建时间
            create_time = None
            if create_time_str:
                try:
                    create_time = datetime.fromisoformat(create_time_str.replace('Z', '+00:00'))
                except Exception:
                    pass

            # 识别消息类型
            message_type = self._identify_message_type(role, user_origin_query, content_str)

            # 解析content字段（JSON数组字符串）
            content_items = []
            try:
                content_items = json.loads(content_str)
            except json.JSONDecodeError:
                logger.warning(f"Content字段解析失败: {content_str[:100]}")

            # 使用ContentParser解析content
            tool_calls, tool_results, text_content = self.content_parser.parse_content(
                content_items, message_type
            )

            # 提取用户查询内容
            user_query = None
            if user_origin_query and user_origin_query.strip():
                user_query = user_origin_query
            elif message_type == MessageType.USER_QUERY:
                # 如果没有userOriginQuery但是消息类型是USER_QUERY，
                # 尝试从text_content中提取用户任务描述
                user_query = self._extract_user_query_from_content(text_content)

            # 创建Message对象
            message = Message(
                message_id=str(message_id) if message_id else None,
                session_id=session_id,
                role=role,
                message_type=message_type,
                content=content_str,
                user_query=user_query,
                tool_calls=tool_calls,
                tool_results=tool_results,
                create_time=create_time,
                user_name=user_name,
                raw_data=data,
            )

            return message

        except Exception as e:
            logger.error(f"解析消息失败: {e}")
            return None

    def _identify_message_type(self, role: str, user_origin_query: str, content_str: str) -> MessageType:
        """
        识别消息类型

        规则:
        - role="USER" 且 userOriginQuery 非空 → USER_QUERY (用户输入)
        - role="USER" 且 userOriginQuery 为空 → TOOL_RESULT (工具返回)
        - role="ASSISTANT" → ASSISTANT (助手输出)

        Args:
            role: 角色
            user_origin_query: 用户原始查询
            content_str: content字段内容

        Returns:
            MessageType
        """
        if role == "USER":
            # 检查是否有userOriginQuery
            if user_origin_query and user_origin_query.strip():
                return MessageType.USER_QUERY

            # 检查content中是否包含tool_result
            try:
                content_items = json.loads(content_str)
                if isinstance(content_items, list):
                    for item in content_items:
                        if isinstance(item, dict) and item.get("type") == "tool_result_text":
                            return MessageType.TOOL_RESULT
            except:
                pass

            # 默认检查content中是否有用户任务标记
            if "user_queried_standard_task" in content_str or "user_referenced_files" in content_str:
                return MessageType.USER_QUERY

            # 其他情况视为工具返回
            return MessageType.TOOL_RESULT

        elif role == "ASSISTANT":
            return MessageType.ASSISTANT

        # 默认返回ASSISTANT
        return MessageType.ASSISTANT

    def _extract_user_query_from_content(self, text_content: str) -> Optional[str]:
        """
        从content中提取用户查询内容

        Args:
            text_content: 文本内容

        Returns:
            用户查询字符串
        """
        if not text_content:
            return None

        # 如果包含user_queried_standard_task标签，识别任务类型
        if "user_queried_standard_task" in text_content:
            # 根据关键词识别任务类型
            if "单元测试" in text_content or "单测" in text_content:
                return "编写单元测试"
            elif "检查代码问题" in text_content and "修复与优化" in text_content:
                return "代码审查与优化"
            elif "代码审查" in text_content or "review" in text_content.lower():
                return "代码审查"
            elif "修复" in text_content or "fix" in text_content.lower():
                return "修复代码问题"
            elif "重构" in text_content or "refactor" in text_content.lower():
                return "代码重构"
            else:
                return "代码相关任务"

        # 从普通用户输入中提取，跳过HTML注释和标签
        lines = text_content.split('\n')
        for line in lines:
            line = line.strip()
            # 跳过空行、HTML注释、XML标签
            if (line and
                not line.startswith('<!--') and
                not line.startswith('<') and
                not line.startswith('```')):
                # 返回第一个有效的文本行
                return line[:100]

        # 默认返回前100个字符（移除换行符）
        cleaned = ' '.join(text_content.split())
        return cleaned[:100].strip() if cleaned else None

    def _truncate_content(self, content: str) -> str:
        """
        智能截断内容,保留关键信息

        Args:
            content: 原始内容

        Returns:
            截断后的内容
        """
        max_length = self.config.max_content_length
        if len(content) <= max_length:
            return content

        # 保留开头和结尾,中间用省略标记
        head = content[:max_length // 2]
        tail = content[-max_length // 2:]
        return f"{head}\n...[TRUNCATED]...\n{tail}"
