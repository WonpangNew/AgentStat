"""
文件操作工具
"""
import os
import json
from typing import List, Iterator
from pathlib import Path
from loguru import logger


class FileUtils:
    """文件操作工具类"""

    @staticmethod
    def find_session_files(input_dir: str) -> List[str]:
        """
        查找所有session文件

        Args:
            input_dir: 输入目录

        Returns:
            session文件路径列表
        """
        session_files = []
        input_path = Path(input_dir)

        if not input_path.exists():
            logger.error(f"输入目录不存在: {input_dir}")
            return session_files

        # 遍历目录查找所有.jsonl文件
        for jsonl_file in input_path.rglob("*.jsonl"):
            session_files.append(str(jsonl_file))

        logger.info(f"找到 {len(session_files)} 个session文件")
        return session_files

    @staticmethod
    def get_output_path(session_file: str, input_dir: str, output_dir: str) -> str:
        """
        根据session文件路径生成对应的输出路径

        Args:
            session_file: session文件路径
            input_dir: 输入目录
            output_dir: 输出目录

        Returns:
            输出文件路径
        """
        # 将 session/日期/sessionId.jsonl 转换为 stat_session/日期/sessionId.json
        rel_path = os.path.relpath(session_file, input_dir)
        output_file = rel_path.replace('.jsonl', '.json')
        return os.path.join(output_dir, output_file)

    @staticmethod
    def ensure_dir(file_path: str):
        """
        确保文件所在目录存在

        Args:
            file_path: 文件路径
        """
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

    @staticmethod
    def save_json(data: dict or list, file_path: str):
        """
        保存JSON文件

        Args:
            data: 数据
            file_path: 文件路径
        """
        FileUtils.ensure_dir(file_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"保存结果到: {file_path}")
