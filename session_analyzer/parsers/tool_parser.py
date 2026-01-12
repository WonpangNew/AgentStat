"""
工具调用解析器
"""
import re
from typing import List, Dict, Optional, Tuple
from loguru import logger

from ..models.message import ToolType, ToolCall, ToolResult


class ToolParser:
    """工具调用解析器 - 从ASSISTANT消息的text中提取工具调用"""

    # 所有工具的XML标签名
    TOOL_TAGS = [
        'codebase_search',
        'delete_file',
        'extract_content_blocks',
        'knowledge_search',
        'list_files',
        'patch_file',
        'preview_page',
        'read_file',
        'read_image',
        'run_command',
        'search_files',
        'subtask',
        'update_memory',
        'use_mcp_tool',
        'web_search',
        'write_file',
    ]

    def parse_tool_calls(self, text: str) -> List[ToolCall]:
        """从文本中解析所有工具调用"""
        tool_calls = []

        for tag in self.TOOL_TAGS:
            pattern = rf'<{tag}>([\s\S]*?)</{tag}>'
            matches = re.findall(pattern, text)

            for match in matches:
                tool_call = self._parse_single_tool(tag, match)
                if tool_call:
                    tool_calls.append(tool_call)

        return tool_calls

    def _parse_single_tool(self, tag: str, content: str) -> Optional[ToolCall]:
        """解析单个工具调用"""
        try:
            tool_type = ToolType(tag)
            params = self._extract_parameters(tag, content)
            file_path = self._extract_file_path(tag, params)
            line_range = self._extract_line_range(tag, params)

            return ToolCall(
                tool_type=tool_type,
                file_path=file_path,
                parameters=params,
                line_range=line_range,
                raw_content=content
            )
        except ValueError:
            logger.warning(f"未知的工具类型: {tag}")
            return None
        except Exception as e:
            logger.error(f"解析工具调用失败 ({tag}): {e}")
            return None

    def _extract_parameters(self, tag: str, content: str) -> Dict:
        """提取工具参数"""
        params = {}

        # 通用参数提取
        param_patterns = {
            'path': r'<path>([\s\S]*?)</path>',
            'pathes': r'<pathes>([\s\S]*?)</pathes>',
            'content': r'<content>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</content>',
            'query': r'<query>([\s\S]*?)</query>',
            'regex': r'<regex>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</regex>',
            'command': r'<command>([\s\S]*?)</command>',
            'url': r'<url>([\s\S]*?)</url>',
            'start_line': r'<start_line>(\d+)</start_line>',
            'end_line': r'<end_line>(\d+)</end_line>',
            'task': r'<task>([\s\S]*?)</task>',
            'tool_name': r'<tool_name>([\s\S]*?)</tool_name>',
            'parameters': r'<parameters>([\s\S]*?)</parameters>',
            'file_pattern': r'<file_pattern>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</file_pattern>',
        }

        for param_name, pattern in param_patterns.items():
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip()
                # 处理CDATA
                if '<![CDATA[' in value:
                    value = re.sub(r'<!\[CDATA\[([\s\S]*?)\]\]>', r'\1', value)
                params[param_name] = value

        return params

    def _extract_file_path(self, tag: str, params: Dict) -> Optional[str]:
        """提取文件路径"""
        # 优先级: path > pathes > file_pattern
        if 'path' in params:
            path = params['path']
            # 处理 path@LINE[start..end] 格式
            if '@' in path:
                return path.split('@')[0].strip()
            return path.strip()

        if 'pathes' in params:
            pathes = params['pathes']
            # 可能包含多个路径,取第一个
            if '@' in pathes:
                return pathes.split('@')[0].strip()
            # 处理多行的情况
            first_line = pathes.strip().split('\n')[0]
            if '@' in first_line:
                return first_line.split('@')[0].strip()
            return first_line.strip()

        if 'file_pattern' in params:
            return params['file_pattern'].strip()

        return None

    def _extract_line_range(self, tag: str, params: Dict) -> Optional[Tuple[int, int]]:
        """提取行范围"""
        # 从 pathes 中提取 LINE[start..end]
        if 'pathes' in params:
            match = re.search(r'LINE\[(\d+)\.\.(\d+)\]', params['pathes'])
            if match:
                return (int(match.group(1)), int(match.group(2)))

        # 从 start_line/end_line 参数提取
        if 'start_line' in params and 'end_line' in params:
            try:
                return (int(params['start_line']), int(params['end_line']))
            except ValueError:
                pass

        return None


class ToolResultParser:
    """工具结果解析器 - 从USER消息(tool_result)中提取结果"""

    def parse_tool_result(self, content_item: Dict) -> Optional[ToolResult]:
        """解析工具结果"""
        if content_item.get('type') != 'tool_result_text':
            return None

        # 提取text字段中的内容
        text = content_item.get('text', '')

        # 提取content字段中的结构化数据
        inner_content = content_item.get('content', {})
        if not isinstance(inner_content, dict):
            inner_content = {}

        tool_name = inner_content.get('toolName', '')
        file_path = inner_content.get('fileFullName', '')
        failed = inner_content.get('failed', False)
        truncated = inner_content.get('truncatedContent', False)

        # 提取结果内容
        tool_result_content = inner_content.get('toolResultContent', {})
        result_text = ''
        if tool_result_content and isinstance(tool_result_content, dict):
            # 结果通常以工具名为key
            result_text = tool_result_content.get(tool_name, '')
            if not result_text:
                # 尝试获取第一个值
                values = list(tool_result_content.values())
                result_text = values[0] if values else ''

        # 如果没有toolResultContent，使用text字段
        if not result_text and text:
            result_text = text

        return ToolResult(
            tool_name=tool_name,
            file_path=file_path if file_path else None,
            content=result_text,
            failed=failed,
            truncated=truncated,
            lines_affected=0  # 后续计算
        )
