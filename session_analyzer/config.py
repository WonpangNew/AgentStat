"""
配置管理模块
"""
from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class Config:
    """系统配置"""

    # LLM配置
    llm_base_url: str = "https://oneapi-comate.baidu-int.com"
    llm_model_id: str = "glm-4.7-internal"
    llm_api_key: str = "sk-rduDvErCxzT33Gsc171d390b05A747CbB4Fa76F87fA56438"

    # 处理配置
    max_content_length: int = 100000  # 单条消息内容最大长度
    batch_size: int = 50              # 批处理消息数量
    max_retries: int = 3              # 最大重试次数

    # 输入输出路径
    input_dir: str = "./session"
    output_dir: str = "./stat_session"

    # 任务识别配置
    task_time_gap_threshold: int = 30  # 任务分割时间阈值（分钟）

    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls(
            llm_base_url=os.getenv("LLM_BASE_URL", cls.llm_base_url),
            llm_model_id=os.getenv("LLM_MODEL_ID", cls.llm_model_id),
            llm_api_key=os.getenv("LLM_API_KEY", cls.llm_api_key),
            input_dir=os.getenv("INPUT_DIR", cls.input_dir),
            output_dir=os.getenv("OUTPUT_DIR", cls.output_dir),
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
        )
