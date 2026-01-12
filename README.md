# Session Analyzer - Coding Agent会话数据分析系统

基于Claude Agent SDK的数据分析Agent，用于分析Coding Agent会话数据，识别任务、统计工具调用、评估任务复杂度等。

## 功能特性

- **会话解析**: 解析JSONL格式的会话数据，识别消息类型（用户输入、工具调用、工具返回）
- **任务识别**: 自动识别会话中的任务边界，支持基于规则和LLM的识别策略
- **工具统计**: 统计16种工具的调用次数（代码搜索、文件读写、命令执行等）
- **文件影响**: 统计被检索、读取、创建、修改、删除的文件数量
- **代码行数**: 统计各类操作影响的代码行数
- **复杂度评估**: 从验证强度、上下文负载、不确定性三个维度评估任务复杂度
- **任务状态**: 判定任务成功/失败状态
- **任务命名**: 基于LLM生成简洁的任务名称

## 项目结构

```
session_analyzer/
├── __init__.py
├── config.py                  # 配置管理
├── main.py                    # 主入口
├── models/                    # 数据模型
│   ├── message.py            # 消息、工具类型定义
│   ├── task.py               # 任务数据模型
│   └── statistics.py         # 统计结果模型
├── parsers/                   # 解析器
│   ├── session_parser.py     # Session文件解析器
│   ├── content_parser.py     # 消息内容解析器
│   └── tool_parser.py        # 工具调用解析器
├── analyzers/                 # 分析器
│   ├── tool_analyzer.py      # 工具调用分析
│   ├── line_counter.py       # 代码行数统计
│   ├── file_counter.py       # 文件影响统计
│   └── complexity_evaluator.py # 复杂度评估
├── agents/                    # LLM Agent
│   ├── llm_client.py         # LLM客户端封装
│   └── task_identifier.py    # 任务识别Agent
├── exporters/                 # 导出器
│   └── json_exporter.py      # JSON结果导出
└── utils/                     # 工具类
    ├── file_utils.py         # 文件操作工具
    └── text_utils.py         # 文本处理工具
```

## 安装

1. 克隆仓库

```bash
git clone <repository-url>
cd AgentStat
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
python run.py
```

### 配置

支持通过环境变量配置：

```bash
export INPUT_DIR="./session"          # 输入目录
export OUTPUT_DIR="./stat_session"    # 输出目录
export LLM_BASE_URL="https://..."     # LLM API地址
export LLM_MODEL_ID="glm-4.7-internal" # 模型ID
export LLM_API_KEY="sk-..."           # API密钥
export LOG_LEVEL="INFO"               # 日志级别

python run.py
```

### 输入格式

输入数据为JSONL格式的会话文件，结构如下：

```
session/
└── 2020-01-08/
    ├── 11475920.jsonl
    ├── 11500658.jsonl
    └── ...
```

每个JSONL文件包含一个会话的所有消息记录。

### 输出格式

输出为JSON格式的统计结果：

```
stat_session/
└── 2020-01-08/
    ├── 11475920.json
    ├── 11500658.json
    └── ...
```

输出JSON结构示例：

```json
[
  {
    "task": "修复DateTimeParseException日期解析问题",
    "status": "success",
    "tool": {
      "codebase_search": 0,
      "search_files": 1,
      "extract_content_blocks": 1,
      "patch_file": 1,
      ...
    },
    "file": {
      "search": 1,
      "read": 1,
      "create": 0,
      "update": 1,
      "delete": 0
    },
    "lines": {
      "search": 3,
      "read": 11,
      "create": 0,
      "update": 1,
      "delete": 0
    },
    "complexity": {
      "level": "simple",
      "reason": "单文件修改,需求明确,无需测试验证"
    },
    "humanTurns": 1
  }
]
```

## 支持的工具类型

系统支持分析以下16种工具：

**搜索类**:
- `codebase_search` - 代码库语义搜索
- `search_files` - 正则搜索文件
- `knowledge_search` - 知识库搜索
- `web_search` - 网页搜索

**读取类**:
- `extract_content_blocks` - 提取代码块
- `read_file` - 读取文件
- `read_image` - 读取图片
- `list_files` - 列出目录
- `preview_page` - 预览页面

**写入类**:
- `write_file` - 写入/创建文件
- `patch_file` - 修改文件
- `delete_file` - 删除文件

**执行类**:
- `run_command` - 运行命令

**辅助类**:
- `subtask` - 子任务拆分
- `update_memory` - 更新记忆
- `use_mcp_tool` - MCP工具调用

## 复杂度评估

系统从三个维度评估任务复杂度：

1. **验证强度**: 是否运行测试/构建命令，是否有多次迭代修复
2. **上下文负载**: 读取的文件数量、代码行数、搜索操作次数
3. **不确定性**: 用户输入轮次、是否有多次澄清对话

最终复杂度分为三个级别：
- `simple`: 简单任务
- `medium`: 中等复杂度
- `complex`: 复杂任务

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black session_analyzer/
```

## License

MIT License

## 作者

Session Analyzer Team
