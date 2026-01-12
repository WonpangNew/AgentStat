"""
任务数据模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from .message import Message


@dataclass
class Task:
    """任务"""
    messages: List[Message] = field(default_factory=list)
    task_name: str = ""
    status: str = "success"  # "success" | "fail"
    boundary_certain: bool = False  # 任务边界是否确定


@dataclass
class TaskStatistics:
    """任务统计结果"""
    task: str  # 任务名称
    status: str  # "success" | "fail"
    tool: Dict[str, int] = field(default_factory=dict)  # 工具调用次数
    file: Dict[str, int] = field(default_factory=dict)  # 文件影响数量
    lines: Dict[str, int] = field(default_factory=dict)  # 代码行数影响
    complexity: Dict[str, Any] = field(default_factory=dict)  # 复杂度评估
    humanTurns: int = 0  # 用户输入轮次

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式用于JSON导出"""
        return {
            "task": self.task,
            "status": self.status,
            "tool": self.tool,
            "file": self.file,
            "lines": self.lines,
            "complexity": self.complexity,
            "humanTurns": self.humanTurns,
        }
