"""
文件影响统计器
"""
import re
from typing import Dict, List, Set, Optional
from loguru import logger

from ..models.message import Message, ToolType, ToolCall, ToolResult
from ..utils.text_utils import TextUtils


class FileCounter:
    """文件影响统计器 - 覆盖所有16种工具"""

    def count_files_for_task(self, messages: List[Message]) -> Dict[str, int]:
        """
        统计任务影响的文件数

        Args:
            messages: 消息列表

        Returns:
            文件影响统计 {"search": n, "read": n, "delete": n, "create": n, "update": n}
        """
        files = {
            "search": set(),   # 被检索到的文件
            "read": set(),     # 被读取的文件
            "delete": set(),   # 被删除的文件
            "create": set(),   # 被创建的文件
            "update": set()    # 被更改的文件
        }

        for message in messages:
            # 处理工具调用
            for tool_call in message.tool_calls:
                self._process_tool_call(tool_call, files)

            # 处理工具结果(补充从结果中提取的文件)
            for tool_result in message.tool_results:
                self._process_tool_result(tool_result, files)

        return {k: len(v) for k, v in files.items()}

    def _process_tool_call(self, tool_call: ToolCall, files: Dict[str, Set[str]]):
        """处理工具调用,提取影响的文件"""
        file_path = tool_call.file_path
        tool_type = tool_call.tool_type

        # ============ 搜索类工具 ============
        if tool_type == ToolType.CODEBASE_SEARCH:
            # 代码库搜索: 搜索路径作为search
            if file_path:
                files["search"].add(file_path)

        elif tool_type == ToolType.SEARCH_FILES:
            # 正则搜索: 搜索路径(目录)
            if file_path:
                files["search"].add(file_path)

        elif tool_type == ToolType.KNOWLEDGE_SEARCH:
            # 知识库搜索: 不涉及具体文件
            pass

        elif tool_type == ToolType.WEB_SEARCH:
            # 网页搜索: 不涉及本地文件
            pass

        # ============ 读取类工具 ============
        elif tool_type == ToolType.EXTRACT_CONTENT_BLOCKS:
            # 提取代码块: 读取指定文件
            if file_path:
                files["read"].add(file_path)

        elif tool_type == ToolType.READ_FILE:
            # 读取文件
            if file_path:
                files["read"].add(file_path)

        elif tool_type == ToolType.READ_IMAGE:
            # 读取图片
            if file_path:
                files["read"].add(file_path)

        elif tool_type == ToolType.LIST_FILES:
            # 列出目录: 目录路径计入read
            if file_path:
                files["read"].add(file_path)

        elif tool_type == ToolType.PREVIEW_PAGE:
            # 预览页面: URL不计入文件
            pass

        # ============ 写入类工具 ============
        elif tool_type == ToolType.WRITE_FILE:
            # 写入文件: 统一计入create
            if file_path:
                files["create"].add(file_path)

        elif tool_type == ToolType.PATCH_FILE:
            # 修改文件
            if file_path:
                files["update"].add(file_path)

        elif tool_type == ToolType.DELETE_FILE:
            # 删除文件
            if file_path:
                files["delete"].add(file_path)

        # ============ 执行类工具 ============
        elif tool_type == ToolType.RUN_COMMAND:
            # 运行命令: 不直接关联文件
            pass

        # ============ 辅助类工具 ============
        # SUBTASK, UPDATE_MEMORY, USE_MCP_TOOL 不直接操作文件

    def _process_tool_result(self, tool_result: ToolResult, files: Dict[str, Set[str]]):
        """从工具结果中补充提取文件信息"""
        tool_name = tool_result.tool_name
        content = tool_result.content

        if not content:
            return

        # 补充文件路径（如果结果中有）
        if tool_result.file_path:
            # 根据工具类型决定归类
            if tool_name in ['codebase_search', 'search_files']:
                files["search"].add(tool_result.file_path)
            elif tool_name in ['extract_content_blocks', 'read_file', 'read_image', 'list_files']:
                files["read"].add(tool_result.file_path)
            elif tool_name == 'write_file':
                files["create"].add(tool_result.file_path)
            elif tool_name == 'patch_file':
                files["update"].add(tool_result.file_path)
            elif tool_name == 'delete_file':
                files["delete"].add(tool_result.file_path)

        # 搜索类工具: 从结果中提取命中的文件
        if tool_name in ['codebase_search', 'search_files']:
            found_files = TextUtils.extract_file_paths(content)
            files["search"].update(found_files)

        # list_files: 从结果中提取列出的文件
        elif tool_name == 'list_files':
            for line in content.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 简单判断是否是文件路径
                    if '/' in line or '\\' in line or '.' in line:
                        files["read"].add(line)
