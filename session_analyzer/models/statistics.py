"""
统计结果模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from .task import TaskStatistics


@dataclass
class SessionStatistics:
    """会话统计结果"""
    session_id: int
    tasks: List[TaskStatistics] = field(default_factory=list)

    def to_dict(self) -> List[Dict[str, Any]]:
        """转换为字典格式用于JSON导出"""
        return [task.to_dict() for task in self.tasks]
