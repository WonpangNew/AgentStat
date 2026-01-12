"""
复杂度评估器
"""
from typing import Dict, List, Any
from ..models.message import Message, MessageType, ToolType


class ComplexityEvaluator:
    """任务复杂度评估器"""

    def evaluate_complexity(
        self,
        messages: List[Message],
        tool_counts: Dict[str, int],
        file_counts: Dict[str, int],
        line_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        评估任务复杂度

        Args:
            messages: 消息列表
            tool_counts: 工具调用次数
            file_counts: 文件影响数量
            line_counts: 代码行数影响

        Returns:
            复杂度评估结果 {"level": "simple|medium|complex", "reason": "..."}
        """
        # 维度1: 验证强度
        verification_score = self._calculate_verification_score(messages, tool_counts)

        # 维度2: 上下文负载
        context_score = self._calculate_context_score(tool_counts, file_counts, line_counts)

        # 维度3: 不确定性
        uncertainty_score = self._calculate_uncertainty_score(messages)

        # 综合评估
        total_score = (verification_score + context_score + uncertainty_score) / 3

        if total_score >= 0.7:
            level = "complex"
        elif total_score >= 0.4:
            level = "medium"
        else:
            level = "simple"

        reason = self._generate_reason(
            level, verification_score, context_score, uncertainty_score,
            tool_counts, file_counts, line_counts, messages
        )

        return {
            "level": level,
            "reason": reason
        }

    def _calculate_verification_score(self, messages: List[Message], tool_counts: Dict[str, int]) -> float:
        """
        计算验证强度得分 (0-1)

        考虑因素:
        - 是否运行了测试/构建命令
        - 测试/构建命令的执行次数
        - 是否有多次迭代修复
        """
        score = 0.0

        # 检查是否有run_command
        run_command_count = tool_counts.get('run_command', 0)
        if run_command_count == 0:
            return 0.0

        # 检查命令内容是否包含测试/构建关键词
        test_keywords = ['test', 'build', 'compile', 'pytest', 'npm test', 'go test', 'mvn test']
        has_test = False
        test_count = 0

        for message in messages:
            for tool_call in message.tool_calls:
                if tool_call.tool_type == ToolType.RUN_COMMAND:
                    command = tool_call.parameters.get('command', '').lower()
                    if any(keyword in command for keyword in test_keywords):
                        has_test = True
                        test_count += 1

        if has_test:
            # 基础分数
            score = 0.3

            # 多次测试表示迭代修复
            if test_count >= 3:
                score = 0.8
            elif test_count >= 2:
                score = 0.6

        return score

    def _calculate_context_score(
        self,
        tool_counts: Dict[str, int],
        file_counts: Dict[str, int],
        line_counts: Dict[str, int]
    ) -> float:
        """
        计算上下文负载得分 (0-1)

        考虑因素:
        - 读取的文件数量和代码行数
        - 搜索操作的次数
        - 涉及的不同文件/模块数量
        """
        # 总文件数
        total_files = sum(file_counts.values())

        # 读取和搜索的代码行数
        total_lines = line_counts.get('read', 0) + line_counts.get('search', 0)

        # 搜索操作次数
        search_count = (
            tool_counts.get('codebase_search', 0) +
            tool_counts.get('search_files', 0) +
            tool_counts.get('knowledge_search', 0)
        )

        # 计算得分
        score = 0.0

        # 文件数量评分
        if total_files >= 10:
            score += 0.4
        elif total_files >= 5:
            score += 0.3
        elif total_files >= 2:
            score += 0.2
        elif total_files >= 1:
            score += 0.1

        # 代码行数评分
        if total_lines >= 1000:
            score += 0.4
        elif total_lines >= 500:
            score += 0.3
        elif total_lines >= 100:
            score += 0.2
        elif total_lines >= 10:
            score += 0.1

        # 搜索次数评分
        if search_count >= 5:
            score += 0.2
        elif search_count >= 2:
            score += 0.1

        return min(score, 1.0)

    def _calculate_uncertainty_score(self, messages: List[Message]) -> float:
        """
        计算不确定性得分 (0-1)

        考虑因素:
        - 用户输入的轮次
        - 是否有多次澄清对话
        - 对话的复杂度
        """
        # 统计用户输入轮次
        user_turns = sum(1 for msg in messages if msg.message_type == MessageType.USER_QUERY)

        score = 0.0

        # 多轮对话表示不确定性
        if user_turns >= 5:
            score = 0.8
        elif user_turns >= 3:
            score = 0.5
        elif user_turns >= 2:
            score = 0.3
        elif user_turns >= 1:
            score = 0.1

        return score

    def _generate_reason(
        self,
        level: str,
        verification_score: float,
        context_score: float,
        uncertainty_score: float,
        tool_counts: Dict[str, int],
        file_counts: Dict[str, int],
        line_counts: Dict[str, int],
        messages: List[Message]
    ) -> str:
        """生成复杂度原因说明"""
        reasons = []

        # 验证强度
        if verification_score >= 0.6:
            reasons.append("包含测试/构建验证")
        elif verification_score > 0:
            reasons.append("有简单验证")
        else:
            reasons.append("无测试验证")

        # 上下文负载
        total_files = sum(file_counts.values())
        if total_files >= 5:
            reasons.append(f"涉及{total_files}个文件")
        elif total_files > 0:
            reasons.append(f"涉及{total_files}个文件")

        total_lines = sum(line_counts.values())
        if total_lines >= 100:
            reasons.append(f"处理{total_lines}行代码")

        # 不确定性
        user_turns = sum(1 for msg in messages if msg.message_type == MessageType.USER_QUERY)
        if user_turns >= 3:
            reasons.append(f"多轮交互({user_turns}轮)")
        elif user_turns >= 2:
            reasons.append(f"{user_turns}轮交互")

        # 工具使用
        total_tools = sum(tool_counts.values())
        if total_tools >= 10:
            reasons.append(f"大量工具调用({total_tools}次)")

        # 特殊情况：无任何操作
        if total_tools == 0:
            reasons = ["纯讨论性任务,无代码操作,无工具调用"]

        return ",".join(reasons) if reasons else "简单任务"
