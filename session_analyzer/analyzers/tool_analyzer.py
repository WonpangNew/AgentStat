"""
工具调用分析器
"""
from typing import Dict, List
from ..models.message import Message, ToolType


class ToolAnalyzer:
    """工具调用分析器"""

    def __init__(self):
        # 初始化所有工具的计数为0
        self.tool_names = [tool.value for tool in ToolType]

    def count_tools(self, messages: List[Message]) -> Dict[str, int]:
        """
        统计工具调用次数

        Args:
            messages: 消息列表

        Returns:
            工具调用次数字典 {tool_name: count}
        """
        tool_counts = {name: 0 for name in self.tool_names}

        for message in messages:
            for tool_call in message.tool_calls:
                tool_name = tool_call.tool_type.value
                tool_counts[tool_name] += 1

        return tool_counts
