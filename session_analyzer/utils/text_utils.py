"""
文本处理工具
"""
import re
from typing import List


class TextUtils:
    """文本处理工具类"""

    @staticmethod
    def count_lines(text: str) -> int:
        """
        统计文本行数

        Args:
            text: 文本内容

        Returns:
            行数
        """
        if not text:
            return 0
        return len(text.strip().split('\n'))

    @staticmethod
    def extract_code_blocks(text: str) -> List[str]:
        """
        从文本中提取代码块

        Args:
            text: 文本内容

        Returns:
            代码块列表
        """
        # 匹配```代码块```
        pattern = r'```[^\n]*\n([\s\S]*?)```'
        matches = re.findall(pattern, text)
        return matches

    @staticmethod
    def extract_file_paths(text: str) -> List[str]:
        """
        从文本中提取文件路径

        Args:
            text: 文本内容

        Returns:
            文件路径列表
        """
        paths = []

        # 匹配 文件路径@LINE[...] 格式
        pattern1 = r'```([^\s@]+)@'
        matches1 = re.findall(pattern1, text)
        paths.extend(matches1)

        # 匹配 文件路径:行号 格式
        pattern2 = r'^([^\s:]+\.\w+):\d+'
        matches2 = re.findall(pattern2, text, re.MULTILINE)
        paths.extend(matches2)

        return list(set(paths))  # 去重

    @staticmethod
    def truncate_text(text: str, max_length: int = 1000) -> str:
        """
        截断文本

        Args:
            text: 文本内容
            max_length: 最大长度

        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text

        return text[:max_length] + "..."
