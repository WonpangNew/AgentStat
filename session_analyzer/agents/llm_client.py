"""
LLM客户端封装
"""
import httpx
from typing import Dict, List, Any, Optional
from loguru import logger


class LLMClient:
    """LLM客户端"""

    def __init__(self, base_url: str, model_id: str, api_key: str, timeout: int = 60):
        """
        初始化LLM客户端

        Args:
            base_url: API基础URL
            model_id: 模型ID
            api_key: API密钥
            timeout: 超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.model_id = model_id
        self.api_key = api_key
        self.client = httpx.Client(timeout=timeout)

    def chat(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        发送chat请求

        Args:
            messages: 消息列表
            tools: 工具定义列表
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            API响应
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        if tools:
            payload["tools"] = tools

        try:
            response = self.client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"LLM API请求失败: {e}")
            raise

    def simple_chat(self, prompt: str, max_tokens: int = 2048) -> str:
        """
        简化的chat接口，直接返回文本响应

        Args:
            prompt: 提示词
            max_tokens: 最大token数

        Returns:
            模型响应文本
        """
        messages = [{"role": "user", "content": prompt}]
        response = self.chat(messages, max_tokens=max_tokens, temperature=0.3)

        # 提取响应内容
        try:
            content = response['choices'][0]['message']['content']
            return content.strip()
        except (KeyError, IndexError) as e:
            logger.error(f"解析LLM响应失败: {e}, response: {response}")
            return ""

    def close(self):
        """关闭客户端连接"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
