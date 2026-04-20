# SuperPipeline Backend 开发规范

> 适用于 server/ 目录下所有 Python 代码

## 技术栈

- Python 3.12
- FastAPI
- pydantic（数据验证）
- pytest（测试）

## 代码组织

```
server/
├── src/
│   └── superpipeline/
│       ├── __init__.py
│       ├── pipeline/        # pipeline 模块
│       ├── material/        # material_collector 模块
│       ├── content/         # content_generator 模块
│       └── audit/          # 审核模块
├── tests/
│   └── unit/
└── config.yaml
```

## 开发规范

### 导入规范

```python
# ✅ 正确
from superpipeline.material.collector import MaterialCollector

# ❌ 错误（不要用相对导入）
from .collector import MaterialCollector
```

### 类型提示

所有公开函数必须有类型提示：

```python
# ✅ 正确
def validate_content(text: str, images: list[str]) -> dict[str, bool]:
    ...

# ❌ 错误
def validate_content(text, images):
    ...
```

### Pydantic 模型

数据类必须使用 pydantic：

```python
from pydantic import BaseModel

class ContentOutput(BaseModel):
    text: str
    images: list[str]
    tags: list[str]

    def validate_for_douyin(self) -> tuple[bool, list[str]]:
        """返回 (是否通过, 错误列表)"""
        ...
```

### FastAPI 路由

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["content"])

@router.post("/generate")
async def generate_content(brief: UserBrief) -> ContentOutput:
    """内容生成接口"""
    ...
```

## 文件命名

- 模块名：`snake_case`（如 `material_collector.py`）
- 测试文件：`test_<module>.py`
- 配置文件：`config.yaml`

## 测试要求

- 每个模块必须有对应的 `tests/unit/test_<module>.py`
- 测试覆盖所有公开函数
- 使用 `pytest` 框架

## Lint & Format

```bash
# 检查
ruff check server/src/

# 自动修复
ruff check --fix server/src/
```

## SuperPipeline 特定规范

### MaterialCollector 约束

- 必须记录素材来源（source_url）
- 禁止在无文档情况下进行 web search
- 素材必须可追溯

### ContentGenerator 约束

- 必须基于输入的 material 生成内容
- 禁止凭空编造内容
- 所有图片必须有来源说明

### Audit 模块约束

- douyin.validate() 必须检查下限（2000字、3张图）
- 风格规则必须包含：无 emoji、像真人写的
- 审核结果必须反馈给 content_generator

## AGENTS.md 位置

本目录的 AGENTS.md：`server/AGENTS.md`
