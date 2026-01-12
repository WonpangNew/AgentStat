"""
消息内容解析器
"""
from typing import List, Tuple
from loguru import logger

from ..models.message import MessageType, ToolCall, ToolResult
from .tool_parser import ToolParser, ToolResultParser


class ContentParser:
    """消息content字段解析器"""

    def __init__(self):
        self.tool_parser = ToolParser()
        self.tool_result_parser = ToolResultParser()

    def parse_content(
        self,
        content_items: List[dict],
        message_type: MessageType
    ) -> Tuple[List[ToolCall], List[ToolResult], str]:
        """
        解析content数组

        Args:
            content_items: content数组
            message_type: 消息类型

        Returns:
            (tool_calls, tool_results, text_content)
        """
        tool_calls = []
        tool_results = []
        text_parts = []

        if not isinstance(content_items, list):
            return tool_calls, tool_results, ""

        for item in content_items:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type", "")

            # 处理text类型 (ASSISTANT消息中的工具调用)
            if item_type == "text" and message_type == MessageType.ASSISTANT:
                text = item.get("text", "")
                if text:
                    text_parts.append(text)
                    # 从text中提取工具调用
                    calls = self.tool_parser.parse_tool_calls(text)
                    tool_calls.extend(calls)

            # 处理tool_result_text类型 (USER消息中的工具返回)
            elif item_type == "tool_result_text" and message_type == MessageType.TOOL_RESULT:
                result = self.tool_result_parser.parse_tool_result(item)
                if result:
                    tool_results.append(result)

            # 处理普通text (USER_QUERY消息)
            elif item_type == "text" and message_type == MessageType.USER_QUERY:
                text = item.get("text", "")
                if text:
                    text_parts.append(text)

        text_content = "\n".join(text_parts)
        return tool_calls, tool_results, text_content
