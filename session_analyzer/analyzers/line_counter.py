"""
代码行数统计器
"""
import re
from typing import Dict, List
from loguru import logger

from ..models.message import Message, ToolType, ToolCall, ToolResult
from ..utils.text_utils import TextUtils


class LineCounter:
    """代码行数计算器 - 覆盖所有16种工具"""

    def count_lines_for_task(self, messages: List[Message]) -> Dict[str, int]:
        """
        统计任务影响的代码行数

        Args:
            messages: 消息列表

        Returns:
            代码行数统计 {"search": n, "read": n, "create": n, "update": n, "delete": n}
        """
        result = {"search": 0, "read": 0, "create": 0, "update": 0, "delete": 0}

        # 建立工具调用和工具结果的映射
        for message in messages:
            for tool_call in message.tool_calls:
                # 找到对应的工具结果
                tool_result = self._find_matching_result(tool_call, messages)

                # 计算行数
                line_counts = self.count_lines_for_tool(tool_call.tool_type, tool_call, tool_result)

                # 累加
                for key in result:
                    result[key] += line_counts.get(key, 0)

        return result

    def _find_matching_result(self, tool_call: ToolCall, messages: List[Message]) -> Optional[ToolResult]:
        """
        查找匹配的工具结果

        简单策略：找到同一消息序列中下一个USER消息的工具结果
        """
        # 遍历messages查找对应的工具结果
        # 这里简化处理，返回第一个匹配工具名的结果
        tool_name = tool_call.tool_type.value

        for message in messages:
            for tool_result in message.tool_results:
                if tool_result.tool_name == tool_name:
                    return tool_result

        return None

    def count_lines_for_tool(
        self,
        tool_type: ToolType,
        tool_call: ToolCall,
        tool_result: Optional[ToolResult]
    ) -> Dict[str, int]:
        """
        根据工具类型计算影响的代码行数

        Returns:
            {"search": n, "read": n, "create": n, "update": n, "delete": n}
        """
        result = {"search": 0, "read": 0, "create": 0, "update": 0, "delete": 0}

        if tool_result is None:
            tool_result = ToolResult(tool_name=tool_type.value)

        # ============ 搜索类工具 ============
        if tool_type == ToolType.CODEBASE_SEARCH:
            result["search"] = self._count_codebase_search_lines(tool_result)

        elif tool_type == ToolType.SEARCH_FILES:
            result["search"] = self._count_search_files_lines(tool_result)

        elif tool_type == ToolType.KNOWLEDGE_SEARCH:
            result["search"] = self._count_knowledge_search_lines(tool_result)

        elif tool_type == ToolType.WEB_SEARCH:
            result["search"] = 0  # 不统计网页搜索

        # ============ 读取类工具 ============
        elif tool_type == ToolType.EXTRACT_CONTENT_BLOCKS:
            result["read"] = self._count_extract_content_blocks_lines(tool_call, tool_result)

        elif tool_type == ToolType.READ_FILE:
            result["read"] = self._count_read_file_lines(tool_call, tool_result)

        elif tool_type == ToolType.READ_IMAGE:
            result["read"] = 0  # 不统计图片

        elif tool_type == ToolType.LIST_FILES:
            result["read"] = self._count_list_files_lines(tool_result)

        elif tool_type == ToolType.PREVIEW_PAGE:
            result["read"] = 0  # 不统计预览

        # ============ 写入类工具 ============
        elif tool_type == ToolType.WRITE_FILE:
            result["create"] = self._count_write_file_lines(tool_call)

        elif tool_type == ToolType.PATCH_FILE:
            update_stats = self._count_patch_file_lines(tool_call)
            result["update"] = update_stats["added"]

        elif tool_type == ToolType.DELETE_FILE:
            result["delete"] = self._count_delete_file_lines(tool_result)

        # ============ 执行类工具 ============
        elif tool_type == ToolType.RUN_COMMAND:
            result["read"] = self._count_run_command_output_lines(tool_result)

        # ============ 辅助类工具 ============
        # SUBTASK, UPDATE_MEMORY, USE_MCP_TOOL 不统计

        return result

    # ============ 具体计算方法 ============

    def _count_codebase_search_lines(self, tool_result: ToolResult) -> int:
        """计算代码库搜索返回的代码行数"""
        if tool_result.failed or not tool_result.content:
            return 0

        # 提取所有代码块并统计行数
        code_blocks = TextUtils.extract_code_blocks(tool_result.content)
        lines = 0
        for block in code_blocks:
            lines += TextUtils.count_lines(block)
        return lines

    def _count_search_files_lines(self, tool_result: ToolResult) -> int:
        """计算正则搜索返回的代码行数"""
        return self._count_codebase_search_lines(tool_result)

    def _count_knowledge_search_lines(self, tool_result: ToolResult) -> int:
        """计算知识库搜索返回的行数"""
        if tool_result.failed or not tool_result.content:
            return 0
        return TextUtils.count_lines(tool_result.content)

    def _count_extract_content_blocks_lines(self, tool_call: ToolCall, tool_result: ToolResult) -> int:
        """计算提取代码块的行数"""
        # 方法1: 从调用参数LINE[start..end]解析
        if tool_call.line_range:
            start, end = tool_call.line_range
            return end - start + 1

        # 方法2: 从结果内容计算
        if tool_result.failed or not tool_result.content:
            return 0

        code_blocks = TextUtils.extract_code_blocks(tool_result.content)
        lines = 0
        for block in code_blocks:
            lines += TextUtils.count_lines(block)
        return lines

    def _count_read_file_lines(self, tool_call: ToolCall, tool_result: ToolResult) -> int:
        """计算读取文件的行数"""
        # 方法1: 从start_line/end_line参数计算
        params = tool_call.parameters
        if params.get('start_line') and params.get('end_line'):
            try:
                start = int(params['start_line'])
                end = int(params['end_line'])
                return end - start + 1
            except:
                pass

        # 方法2: 从结果内容计算
        if tool_result.failed or not tool_result.content:
            return 0
        return TextUtils.count_lines(tool_result.content)

    def _count_list_files_lines(self, tool_result: ToolResult) -> int:
        """计算列出的文件/目录数量"""
        if tool_result.failed or not tool_result.content:
            return 0
        return TextUtils.count_lines(tool_result.content)

    def _count_write_file_lines(self, tool_call: ToolCall) -> int:
        """计算写入文件的行数"""
        content = tool_call.parameters.get('content', '')
        if not content:
            return 0
        return TextUtils.count_lines(content)

    def _count_patch_file_lines(self, tool_call: ToolCall) -> Dict[str, int]:
        """
        计算patch修改的行数
        返回: {"removed": 删除的行数, "added": 新增的行数}
        """
        content = tool_call.parameters.get('content', '')
        if not content:
            return {"removed": 0, "added": 0}

        removed = 0
        added = 0

        # 解析所有的 SEARCH/REPLACED_BY 块
        # 格式: <<< SEARCH <<<\n旧代码\n==== REPLACED_BY ====\n新代码\n>>> END >>>
        pattern = r'<<< SEARCH <<<\s*([\s\S]*?)\s*==== REPLACED_BY ====\s*([\s\S]*?)\s*>>> END >>>'
        matches = re.findall(pattern, content)

        for old_code, new_code in matches:
            removed += TextUtils.count_lines(old_code)
            added += TextUtils.count_lines(new_code)

        return {"removed": removed, "added": added}

    def _count_delete_file_lines(self, tool_result: ToolResult) -> int:
        """计算删除文件的原行数"""
        if tool_result.failed:
            return 0

        # 尝试从结果中解析文件行数信息
        match = re.search(r'(\d+)\s*lines?', tool_result.content, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0

    def _count_run_command_output_lines(self, tool_result: ToolResult) -> int:
        """计算命令输出的行数"""
        if tool_result.failed or not tool_result.content:
            return 0
        return TextUtils.count_lines(tool_result.content)


from typing import Optional
