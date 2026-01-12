"""
主程序入口
"""
import sys
from pathlib import Path
from loguru import logger
from tqdm import tqdm

from .config import Config
from .parsers import SessionParser
from .analyzers import ToolAnalyzer, LineCounter, FileCounter, ComplexityEvaluator
from .agents import LLMClient, TaskIdentifier
from .exporters import JSONExporter
from .models import SessionStatistics, TaskStatistics, MessageType
from .utils import FileUtils


class SessionAnalyzer:
    """会话分析器主类"""

    def __init__(self, config: Config):
        """
        初始化会话分析器

        Args:
            config: 配置对象
        """
        self.config = config

        # 初始化各个组件
        self.session_parser = SessionParser(config)
        self.tool_analyzer = ToolAnalyzer()
        self.line_counter = LineCounter()
        self.file_counter = FileCounter()
        self.complexity_evaluator = ComplexityEvaluator()

        # 初始化LLM相关组件
        self.llm_client = LLMClient(
            base_url=config.llm_base_url,
            model_id=config.llm_model_id,
            api_key=config.llm_api_key
        )
        self.task_identifier = TaskIdentifier(
            llm_client=self.llm_client,
            time_gap_threshold=config.task_time_gap_threshold
        )

        self.exporter = JSONExporter()

    def analyze_session(self, session_file: str) -> SessionStatistics:
        """
        分析单个session文件

        Args:
            session_file: session文件路径

        Returns:
            会话统计结果
        """
        logger.info(f"开始分析session: {session_file}")

        # 1. 解析session文件
        messages = list(self.session_parser.parse_session(session_file))
        if not messages:
            logger.warning(f"Session文件为空或解析失败: {session_file}")
            return SessionStatistics(session_id=0, tasks=[])

        session_id = messages[0].session_id if messages else 0

        # 2. 识别任务
        logger.debug(f"识别任务边界...")
        tasks = self.task_identifier.identify_tasks(messages)
        logger.info(f"识别到 {len(tasks)} 个任务")

        # 3. 分析每个任务
        task_stats_list = []
        for i, task in enumerate(tasks, 1):
            logger.debug(f"分析任务 {i}/{len(tasks)}: {task.task_name}")
            task_stats = self._analyze_task(task)
            task_stats_list.append(task_stats)

        # 4. 创建会话统计结果
        statistics = SessionStatistics(
            session_id=session_id,
            tasks=task_stats_list
        )

        return statistics

    def _analyze_task(self, task) -> TaskStatistics:
        """
        分析单个任务

        Args:
            task: 任务对象

        Returns:
            任务统计结果
        """
        messages = task.messages

        # 1. 统计工具调用次数
        tool_counts = self.tool_analyzer.count_tools(messages)

        # 2. 统计文件影响
        file_counts = self.file_counter.count_files_for_task(messages)

        # 3. 统计代码行数
        line_counts = self.line_counter.count_lines_for_task(messages)

        # 4. 评估复杂度
        complexity = self.complexity_evaluator.evaluate_complexity(
            messages, tool_counts, file_counts, line_counts
        )

        # 5. 统计用户反馈轮次
        human_turns = sum(1 for msg in messages if msg.message_type == MessageType.USER_QUERY)

        # 6. 创建任务统计结果
        task_stats = TaskStatistics(
            task=task.task_name,
            status=task.status,
            tool=tool_counts,
            file=file_counts,
            lines=line_counts,
            complexity=complexity,
            humanTurns=human_turns
        )

        return task_stats

    def process_all_sessions(self):
        """处理所有session文件"""
        logger.info("开始处理所有session文件...")

        # 1. 查找所有session文件
        session_files = FileUtils.find_session_files(self.config.input_dir)
        if not session_files:
            logger.error(f"未找到任何session文件: {self.config.input_dir}")
            return

        logger.info(f"找到 {len(session_files)} 个session文件")

        # 2. 处理每个session
        success_count = 0
        fail_count = 0

        for session_file in tqdm(session_files, desc="处理session"):
            try:
                # 分析session
                statistics = self.analyze_session(session_file)

                # 生成输出路径
                output_path = FileUtils.get_output_path(
                    session_file, self.config.input_dir, self.config.output_dir
                )

                # 导出结果
                self.exporter.export(statistics, output_path)

                success_count += 1

            except Exception as e:
                logger.error(f"处理session失败 ({session_file}): {e}")
                fail_count += 1
                continue

        logger.info(f"处理完成! 成功: {success_count}, 失败: {fail_count}")

    def close(self):
        """关闭资源"""
        self.llm_client.close()


def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # 加载配置
    config = Config.from_env()

    # 创建分析器
    analyzer = SessionAnalyzer(config)

    try:
        # 处理所有session
        analyzer.process_all_sessions()
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
