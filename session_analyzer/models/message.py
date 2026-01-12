"""
消息数据模型
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class MessageType(Enum):
    """消息类型"""
    USER_QUERY = "user_query"       # 用户输入
    TOOL_RESULT = "tool_result"     # 工具返回
    ASSISTANT = "assistant"          # 助手输出


class ToolType(Enum):
    """完整的工具类型枚举 - 共16种工具"""

    # === 代码搜索类 ===
    CODEBASE_SEARCH = "codebase_search"                # 代码库语义搜索
    SEARCH_FILES = "search_files"                      # 正则搜索文件
    KNOWLEDGE_SEARCH = "knowledge_search"              # 知识库搜索
    WEB_SEARCH = "web_search"                          # 网页搜索

    # === 文件读取类 ===
    EXTRACT_CONTENT_BLOCKS = "extract_content_blocks"  # 提取代码块
    READ_FILE = "read_file"                            # 读取文件
    READ_IMAGE = "read_image"                          # 读取图片
    LIST_FILES = "list_files"                          # 列出目录
    PREVIEW_PAGE = "preview_page"                      # 预览页面

    # === 文件写入类 ===
    WRITE_FILE = "write_file"                          # 写入/创建文件
    PATCH_FILE = "patch_file"                          # 修改文件
    DELETE_FILE = "delete_file"                        # 删除文件

    # === 执行类 ===
    RUN_COMMAND = "run_command"                        # 运行命令

    # === 辅助类 ===
    SUBTASK = "subtask"                                # 子任务拆分
    UPDATE_MEMORY = "update_memory"                    # 更新记忆
    USE_MCP_TOOL = "use_mcp_tool"                      # MCP工具调用


# 工具分类映射
TOOL_CATEGORIES = {
    "search": [
        ToolType.CODEBASE_SEARCH,
        ToolType.SEARCH_FILES,
        ToolType.KNOWLEDGE_SEARCH,
        ToolType.WEB_SEARCH,
    ],
    "read": [
        ToolType.EXTRACT_CONTENT_BLOCKS,
        ToolType.READ_FILE,
        ToolType.READ_IMAGE,
        ToolType.LIST_FILES,
        ToolType.PREVIEW_PAGE,
    ],
    "create": [
        ToolType.WRITE_FILE,
    ],
    "update": [
        ToolType.PATCH_FILE,
    ],
    "delete": [
        ToolType.DELETE_FILE,
    ],
    "execute": [
        ToolType.RUN_COMMAND,
    ],
    "auxiliary": [
        ToolType.SUBTASK,
        ToolType.UPDATE_MEMORY,
        ToolType.USE_MCP_TOOL,
    ],
}


@dataclass
class ToolCall:
    """工具调用"""
    tool_type: ToolType
    file_path: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    line_range: Optional[tuple] = None  # (start, end) for extract_content_blocks/read_file
    raw_content: str = ""  # 原始的工具调用内容


@dataclass
class ToolResult:
    """工具结果"""
    tool_name: str
    file_path: Optional[str] = None
    content: str = ""
    failed: bool = False
    truncated: bool = False
    lines_affected: int = 0  # 影响的代码行数（后续计算）


@dataclass
class Message:
    """消息"""
    message_id: Optional[str] = None
    session_id: int = 0
    role: str = ""  # "USER" or "ASSISTANT"
    message_type: MessageType = MessageType.ASSISTANT
    content: str = ""  # 原始content字符串
    user_query: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    create_time: Optional[datetime] = None
    user_name: str = ""

    # 额外的元数据
    raw_data: Dict[str, Any] = field(default_factory=dict)
