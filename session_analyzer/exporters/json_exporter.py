"""
JSON结果导出器
"""
from typing import List
from loguru import logger

from ..models.statistics import SessionStatistics
from ..utils.file_utils import FileUtils


class JSONExporter:
    """JSON结果导出器"""

    def export(self, statistics: SessionStatistics, output_path: str):
        """
        导出统计结果到JSON文件

        Args:
            statistics: 会话统计结果
            output_path: 输出文件路径
        """
        try:
            data = statistics.to_dict()
            FileUtils.save_json(data, output_path)
            logger.info(f"成功导出统计结果: {output_path}")
        except Exception as e:
            logger.error(f"导出统计结果失败 ({output_path}): {e}")
            raise
