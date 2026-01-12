"""
任务识别Agent
"""
from typing import List, Tuple
from datetime import datetime, timedelta
from loguru import logger

from ..models.message import Message, MessageType
from ..models.task import Task
from .llm_client import LLMClient
from ..utils.text_utils import TextUtils


class TaskIdentifier:
    """任务识别器 - 使用LLM识别任务边界、生成任务名称、判定任务状态"""

    def __init__(self, llm_client: LLMClient, time_gap_threshold: int = 30):
        """
        初始化任务识别器

        Args:
            llm_client: LLM客户端
            time_gap_threshold: 任务分割时间阈值（分钟）
        """
        self.llm_client = llm_client
        self.time_gap_threshold = time_gap_threshold

    def identify_tasks(self, messages: List[Message]) -> List[Task]:
        """
        识别任务列表

        Args:
            messages: 消息列表

        Returns:
            任务列表
        """
        if not messages:
            return []

        # 策略1: 先用规则快速分割明显的任务边界
        preliminary_tasks = self._rule_based_split(messages)

        # 策略2: 对不确定的边界使用LLM确认（可选，为了性能暂时禁用）
        # final_tasks = self._llm_refine_boundaries(preliminary_tasks)

        # 为每个任务生成名称
        for task in preliminary_tasks:
            task.task_name = self._generate_task_name(task)
            task.status = self._evaluate_task_status(task)

        return preliminary_tasks

    def _rule_based_split(self, messages: List[Message]) -> List[Task]:
        """
        基于规则的快速任务分割

        规则:
        1. 时间间隔超过阈值
        2. 明显的任务结束语
        3. 新的用户输入且前一个任务有明确结束标志
        """
        tasks = []
        current_task = None

        for i, msg in enumerate(messages):
            if msg.message_type == MessageType.USER_QUERY:
                # 检查是否应该开始新任务
                should_start_new = False

                if current_task is None:
                    # 第一个用户输入，开始新任务
                    should_start_new = True
                else:
                    # 检查时间间隔
                    if self._check_time_gap(current_task.messages[-1], msg):
                        should_start_new = True
                    # 检查是否是新任务的标志
                    elif self._is_new_task_signal(msg, current_task):
                        should_start_new = True

                if should_start_new:
                    if current_task:
                        current_task.boundary_certain = True
                        tasks.append(current_task)
                    current_task = Task(messages=[msg])
                else:
                    if current_task:
                        current_task.messages.append(msg)
            else:
                # ASSISTANT 或 TOOL_RESULT
                if current_task:
                    current_task.messages.append(msg)

        # 添加最后一个任务
        if current_task:
            current_task.boundary_certain = True
            tasks.append(current_task)

        return tasks

    def _check_time_gap(self, prev_msg: Message, curr_msg: Message) -> bool:
        """检查时间间隔是否超过阈值"""
        if not prev_msg.create_time or not curr_msg.create_time:
            return False

        time_diff = curr_msg.create_time - prev_msg.create_time
        return time_diff > timedelta(minutes=self.time_gap_threshold)

    def _is_new_task_signal(self, msg: Message, current_task: Task) -> bool:
        """
        判断是否是新任务的信号

        检查因素:
        - 用户输入包含明显的新任务关键词
        - 与当前任务的语义相关性低
        """
        if not msg.user_query:
            return False

        query_lower = msg.user_query.lower()

        # 新任务关键词
        new_task_keywords = [
            '下一个', '另外', '接下来', '换个', '新的',
            'next', 'another', 'also', 'additionally',
            '第二个', '第三个', '第四个',
        ]

        for keyword in new_task_keywords:
            if keyword in query_lower:
                return True

        return False

    def _generate_task_name(self, task: Task) -> str:
        """
        生成任务名称

        策略:
        1. 优先从第一个用户输入提取
        2. 如果第一个输入过长或不清晰，使用LLM总结
        """
        if not task.messages:
            return "未知任务"

        # 找到所有用户查询
        user_queries = [
            msg.user_query for msg in task.messages
            if msg.message_type == MessageType.USER_QUERY and msg.user_query
        ]

        if not user_queries:
            return "无用户输入任务"

        first_query = user_queries[0]

        # 如果第一个查询简短清晰，直接使用
        if len(first_query) <= 100 and '\n' not in first_query:
            return TextUtils.truncate_text(first_query, 50)

        # 否则使用LLM总结
        try:
            return self._llm_generate_task_name(user_queries, task)
        except Exception as e:
            logger.warning(f"LLM生成任务名称失败: {e}")
            # 降级策略：取第一句话
            first_line = first_query.split('\n')[0]
            return TextUtils.truncate_text(first_line, 50)

    def _llm_generate_task_name(self, user_queries: List[str], task: Task) -> str:
        """使用LLM生成任务名称"""
        # 构建prompt
        queries_text = "\n".join([f"{i+1}. {q[:200]}" for i, q in enumerate(user_queries[:3])])

        # 统计工具调用
        tool_summary = self._summarize_tools(task)

        prompt = f"""请根据以下信息，用一句话（不超过50字）总结这个编程任务的核心内容：

用户输入：
{queries_text}

工具调用情况：
{tool_summary}

要求：
1. 只返回任务名称，不要有其他解释
2. 简洁明了，突出任务核心
3. 使用中文
4. 不超过50字

任务名称："""

        response = self.llm_client.simple_chat(prompt, max_tokens=100)
        task_name = response.strip().strip('"\'')

        # 如果LLM返回过长，截断
        return TextUtils.truncate_text(task_name, 50)

    def _summarize_tools(self, task: Task) -> str:
        """总结任务中的工具调用"""
        tool_counts = {}
        for msg in task.messages:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.tool_type.value
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        if not tool_counts:
            return "无工具调用"

        # 列出前3个最常用的工具
        sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        tool_list = [f"{name}({count}次)" for name, count in sorted_tools]
        return ", ".join(tool_list)

    def _evaluate_task_status(self, task: Task) -> str:
        """
        评估任务状态

        策略:
        1. 检查是否有明显的错误/失败信息
        2. 检查最后的用户反馈是否为正面
        3. 默认为成功
        """
        if not task.messages:
            return "success"

        # 检查最后几条消息
        last_messages = task.messages[-3:]

        # 查找失败信号
        failure_keywords = [
            'error', 'fail', 'failed', '失败', '错误',
            'exception', 'bug', '不行', '不对',
        ]

        for msg in last_messages:
            if msg.message_type == MessageType.USER_QUERY and msg.user_query:
                query_lower = msg.user_query.lower()
                if any(keyword in query_lower for keyword in failure_keywords):
                    # 用户报告问题，可能失败
                    return "fail"

            # 检查工具结果
            for tool_result in msg.tool_results:
                if tool_result.failed:
                    return "fail"

        # 检查是否有明显的成功信号
        success_keywords = [
            '好的', '谢谢', '可以', '成功', 'thanks', 'ok', 'good',
            '完成', 'done', '没问题',
        ]

        for msg in reversed(last_messages):
            if msg.message_type == MessageType.USER_QUERY and msg.user_query:
                query_lower = msg.user_query.lower()
                if any(keyword in query_lower for keyword in success_keywords):
                    return "success"

        # 默认为成功
        return "success"

    def _llm_refine_boundaries(self, tasks: List[Task]) -> List[Task]:
        """
        使用LLM精化任务边界（可选，性能考虑暂不启用）

        对于boundary_certain=False的任务，使用LLM判断是否应该合并
        """
        # TODO: 实现LLM边界精化逻辑
        return tasks
