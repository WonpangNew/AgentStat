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

            # 创建Message对象
            message = Message(
                message_id=str(message_id) if message_id else None,
                session_id=session_id,
                role=role,
                message_type=message_type,
                content=content_str,
                user_query=user_origin_query if user_origin_query else None,
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
