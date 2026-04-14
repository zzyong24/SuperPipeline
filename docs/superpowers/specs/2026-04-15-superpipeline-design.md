# SuperPipeline — 全媒体内容生产管线设计文档

> 日期：2026-04-15
> 状态：Approved
> 作者：MoonlitClear + Claude

## 1. 项目定位

将选题、素材、生成、编辑、审核、分发、复盘全流程自动化的多 Agent 内容生产系统。

**核心原则**：一次配置、批量产出、全链路可控、多平台分发。

**MVP 范围**：图文内容（个人使用），覆盖完整生产链路。视频和多用户后续扩展。

## 2. 核心决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 架构模式 | Hub-Spoke 调度器 | 支持多平台并行生成、Agent 独立可测、YAML 配置扩展 |
| Agent 通信 | LangGraph State 驱动 | 原生数据驱动，无需额外 Event Bus 抽象层 |
| 编排框架 | LangGraph | 图编排、状态机、断点续跑、subgraph 原生支持 |
| 技术栈 | Python | AI SDK 生态成熟，开发效率高 |
| 文本/图片模型 | MiniMax（可插拔） | 当前可用，后续通过 Adapter 模式切换 |
| 数据存储 | SQLite + 本地文件 | MVP 轻量，元数据用 SQLite，内容资产用文件 |
| 内容类型 | 参数化（prompt/skill 控制） | 管道是引擎，类型是配方，不硬编码 |
| 触发方式 | 渐进式（MVP 手动触发） | 架构预留调度接口，后续可接 cron/事件驱动 |
| 发布方式 | 手动发布 | 防封控，审核由 Agent 自动完成，发布人工操作 |
| 目标平台 | X、小红书、抖音、B站 | 主流平台，通过平台适配层扩展 |

## 3. 系统架构

### 3.1 分层架构

```
┌─────────────────────────────────┐
│  Clients                        │
│  CLI (MVP) / API / 小程序 / APP │
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│  API Layer (FastAPI)            │
│  MVP 阶段先做 CLI，API 后加     │
│  core 层接口从第一天按可被调用设计│
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│  Core Engine                    │
│  Orchestrator (LangGraph)       │
│  Registry / State / Models      │
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│  Agents (可插拔模块)             │
│  选题 / 素材 / 生成 / 审核 / 复盘│
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│  Infrastructure                 │
│  Storage / Model Adapters       │
└─────────────────────────────────┘
```

### 3.2 Agent 通信模式

Agent 之间通过 LangGraph 的 State 解耦，不直接调用：

- 每个 Agent 声明 `consumes`（从 State 读什么）和 `produces`（往 State 写什么）
- Orchestrator 根据 YAML 配置决定流转顺序
- Agent 之间零依赖——移除任何一个 Agent，其他 Agent 不受影响

### 3.3 MVP 管道流程

```
用户输入 Brief
       │
       ▼
  选题 Agent ── 生成候选选题，自动或人工选中一个
       │
       ▼
  素材 Agent ── 联网搜索 + 本地知识库采集素材
       │
       ▼
  生成 Agent ── 按平台规范生成图文（可并行多平台）
       │
       ▼
  审核 Agent ── 质量评分 + 平台合规检查
       │
       ▼
  待发布队列 ── 人工确认发布
       │
       ▼
  复盘 Agent ── 分析数据、生成改进建议
```

## 4. 项目结构

```
SuperPipeline/
├── docs/                          # 文档
│   ├── architecture.md            # 架构总览
│   ├── agent-dev-guide.md         # 如何写一个新 Agent
│   └── superpowers/specs/         # 设计文档
│
├── src/
│   ├── core/                      # 核心引擎（稳定层）
│   │   ├── orchestrator.py        # LangGraph 图构建器，读 YAML 动态组装管道
│   │   ├── state.py               # PipelineState 定义
│   │   ├── registry.py            # Agent 注册表（自动发现 + 注册）
│   │   ├── models.py              # 模型适配器（可插拔）
│   │   └── config.py              # 全局配置加载
│   │
│   ├── agents/                    # Agent 模块（每个 Agent 一个目录）
│   │   ├── base.py                # BaseAgent 抽象类
│   │   ├── topic_generator/       # 选题 Agent
│   │   │   ├── __init__.py        # 注册入口
│   │   │   ├── agent.py           # 核心逻辑
│   │   │   ├── prompts/           # prompt 模板（Jinja2）
│   │   │   ├── schemas.py         # 输入/输出/配置 Schema
│   │   │   └── README.md          # Agent 说明文档
│   │   ├── material_collector/    # 素材 Agent
│   │   ├── content_generator/     # 生成 Agent
│   │   ├── reviewer/              # 审核 Agent
│   │   └── analyst/               # 复盘 Agent
│   │
│   ├── platforms/                 # 平台适配层
│   │   ├── base.py                # BasePlatform 抽象类
│   │   ├── xiaohongshu.py         # 小红书规范
│   │   ├── x_twitter.py           # X 规范
│   │   ├── douyin.py              # 抖音规范
│   │   └── bilibili.py            # B站规范
│   │
│   ├── api/                       # API 层（MVP 后期加）
│   │   ├── app.py                 # FastAPI 入口
│   │   ├── routes/                # 路由
│   │   └── schemas.py             # API Schema
│   │
│   └── storage/                   # 存储层
│       ├── state_store.py         # SQLite 状态持久化
│       ├── asset_store.py         # 文件存储
│       └── models.py              # DB Schema
│
├── pipelines/                     # 管道配置（YAML）
│   ├── xiaohongshu_image_text.yaml
│   ├── x_thread.yaml
│   └── bilibili_article.yaml
│
├── prompts/                       # 全局 prompt 库
│   ├── styles/                    # 风格模板
│   └── platforms/                 # 平台规范 prompt
│
├── tests/
│   ├── agents/                    # Agent 独立测试
│   └── integration/               # 端到端管道测试
│
├── data/                          # 运行时数据（.gitignore）
│   ├── assets/                    # 图片、素材文件
│   ├── outputs/                   # 生成的内容
│   └── superpipeline.db           # SQLite
│
├── config.yaml                    # 全局配置（模型、存储等）
├── pyproject.toml
└── README.md
```

## 5. 核心接口设计

### 5.1 PipelineState（数据契约）

```python
class PipelineState(TypedDict):
    # 运行标识
    run_id: str
    pipeline_config: PipelineConfig
    user_brief: UserBrief

    # 选题阶段
    topics: list[Topic]
    selected_topic: Optional[Topic]

    # 素材阶段
    materials: list[Material]

    # 生成阶段（按平台分）
    contents: dict[str, PlatformContent]

    # 审核阶段
    reviews: dict[str, ReviewResult]

    # 复盘阶段
    analysis: Optional[Analysis]

    # 流转控制
    stage: str
    errors: list[PipelineError]
    metadata: dict
```

### 5.2 BaseAgent（Agent 标准接口）

```python
class BaseAgent(ABC):
    name: str
    consumes: list[str]            # 从 State 读哪些字段
    produces: list[str]            # 往 State 写哪些字段
    config_schema: type[BaseModel] # 配置 Schema

    @abstractmethod
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        """
        inputs: 从 State 中按 consumes 提取的字段
        config: 从 YAML 加载的运行时配置
        return: 要写回 State 的字段（对应 produces）
        """

    def validate_inputs(self, state: PipelineState) -> bool:
        """自动校验 consumes 字段是否在 State 中且非空"""

    def validate_outputs(self, outputs: dict) -> bool:
        """自动校验 outputs 是否符合 produces 声明"""
```

### 5.3 Agent 注册与发现

```python
@register_agent
class TopicGeneratorAgent(BaseAgent):
    name = "topic_generator"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = TopicGenConfig

    async def run(self, inputs, config):
        brief = inputs["user_brief"]
        prompt = self.load_prompt("generate.j2", brief=brief, **config.dict())
        response = await self.model.generate(prompt)
        return {"topics": self.parse_topics(response)}
```

新增 Agent = 写一个模块 + 注册 + YAML 里加一行。不改 Orchestrator 代码。

### 5.4 模型适配器

```python
class ModelAdapter(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """文本生成"""

    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """图片生成"""

class MiniMaxAdapter(ModelAdapter):
    """当前默认"""

class OpenAICompatibleAdapter(ModelAdapter):
    """兼容 OpenAI 接口的模型（后续扩展）"""
```

模型配置：

```yaml
models:
  text:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    model: abab6.5-chat
  image:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    model: abab6.5-image
```

换模型 = 改 YAML + 写一个 Adapter 类。

### 5.5 Orchestrator（动态图构建）

```python
class Orchestrator:
    def build_graph(self, pipeline_config: PipelineConfig) -> StateGraph:
        graph = StateGraph(PipelineState)

        for stage in pipeline_config.stages:
            agent = self.registry.get(stage.agent)
            graph.add_node(stage.agent, self._wrap_agent(agent, stage.config))

        self._build_edges(graph, pipeline_config)
        return graph.compile(checkpointer=self.checkpointer)
```

Orchestrator 不知道任何具体 Agent 的存在。它只认识注册表和 YAML。

### 5.6 Pipeline YAML 配置

```yaml
name: 小红书图文
description: 生成小红书种草图文内容
platforms: [xiaohongshu]

stages:
  - agent: topic_generator
    config:
      style: "种草"
      count: 5
  - agent: material_collector
    config:
      sources: ["web", "local_kb"]
  - agent: content_generator
    config:
      platform: xiaohongshu
      format: image_text
  - agent: reviewer
    config:
      rules: ["platform_compliance", "quality_score"]
      min_score: 7.0
  - agent: analyst
    config:
      trigger: after_publish
      metrics: ["engagement", "reach"]
```

### 5.7 Core 层函数接口（CLI / API / 小程序通用）

```python
async def run_pipeline(config_name: str, brief: UserBrief) -> str:
    """触发管道，返回 run_id"""

async def get_run_status(run_id: str) -> RunStatus:
    """查询运行状态和当前阶段"""

async def get_run_outputs(run_id: str) -> dict[str, PlatformContent]:
    """获取生成的内容"""

async def approve_content(run_id: str, platform: str) -> bool:
    """标记内容为已发布，触发复盘"""
```

## 6. 平台适配层

```python
class BasePlatform(ABC):
    name: str
    max_text_length: int
    image_specs: ImageSpec          # 尺寸、格式、数量限制
    tag_rules: TagRules             # 标签/话题规范
    content_rules: list[str]        # 平台禁忌/合规规则

    @abstractmethod
    def format_content(self, raw_content: str) -> str:
        """按平台规范格式化内容"""

    @abstractmethod
    def validate(self, content: PlatformContent) -> list[str]:
        """校验是否符合平台规范，返回问题列表"""
```

平台规范以配置 + 代码双重定义。审核 Agent 调用 `platform.validate()` 做合规检查。

## 7. 存储设计

### SQLite（元数据 + 状态）

- `pipeline_runs`: 运行记录（run_id, config, status, timestamps）
- `contents`: 内容记录（run_id, platform, content, review_score, publish_status）
- `analytics`: 复盘数据（content_id, metrics, insights）

### 文件系统（内容资产）

```
data/
├── assets/{run_id}/           # 素材文件
├── outputs/{run_id}/          # 生成内容（文本 + 图片）
└── superpipeline.db
```

## 8. 错误处理策略

- Agent 级别：每个 Agent 的错误写入 `state.errors`，不中断管道
- 管道级别：可配置 `on_error: skip | retry | halt`
- 重试：Agent 级别可配置重试次数和退避策略
- 断点续跑：LangGraph checkpointer 支持从失败点恢复

## 9. 扩展路径

| 阶段 | 新增内容 | 改动范围 |
|------|---------|---------|
| 加新平台 | `platforms/` 加一个文件 + YAML | 不改 core |
| 加新 Agent | `agents/` 加一个目录 + YAML | 不改 core |
| 换模型 | `core/models.py` 加 Adapter + 改 config | 不改 agents |
| 加 API 层 | `api/` 目录，调 core 函数 | 不改 core/agents |
| 加视频 | 新 Agent + 新 Pipeline YAML | 不改已有模块 |
| 全自动调度 | 加 scheduler 模块，调 core 函数 | 不改 core/agents |

## 10. MVP 交付物

1. 核心引擎：Orchestrator + Registry + State + ModelAdapter
2. 5 个 Agent：选题、素材、生成、审核、复盘
3. 2 个平台适配：小红书 + X
4. 1 个 Pipeline YAML：小红书图文
5. CLI 入口：命令行触发和查看
6. 文档：架构文档 + Agent 开发指南
7. 测试：每个 Agent 独立测试 + 一个端到端测试
