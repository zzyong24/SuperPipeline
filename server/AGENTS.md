<!-- GENERATOR: This file is managed by the harness system. Do not remove this comment. -->

# SuperPipeline Server Generator 约束

> 本文件是三层架构的约束层落地，位于 server/ 目录

## 技术栈约束

- Python 3.12
- FastAPI + pydantic
- pytest
- ruff（lint）

## 开发规范

- ✅ 所有公开函数必须有类型提示
- ✅ 使用 pydantic 作为数据验证
- ✅ 每个模块必须有对应的 `tests/unit/test_<module>.py`
- ✅ 导入：`from superpipeline.<module> import ...`，禁止相对导入
- ✅ Lint：`ruff check server/src/`

## Generator 职责

- 读取 `.harness/sprint_contracts/sprint_20260421_1.json` 获取当前任务
- 读取 `.harness/feature_list.json` 确认当前 feature 和 phase
- **禁止跳 phase**（phase=1 plan → phase=2 implement → phase=3 verify → phase=4 deliver）
- 完成后更新 feature_list.json 中的 phase
- 在 `.harness/eval_log.jsonl` 追加执行记录

## SuperPipeline 特定约束

- material_collector 必须记录 source_url
- content_generator 必须基于 material 生成，禁止凭空编造
- audit 模块：douyin.validate() 必须有下限检查（2000字、3张图）
- 审核结果必须反馈给 content_generator

## 当前 feature（phase=2）

- f001: SuperPipeline Harness 工程化（phase=2 implement）
- f001-1: Harness 文件层初始化（phase=2 implement）

## 相关路径

| 文件 | 路径 |
|------|------|
| 项目根 AGENTS | `../AGENTS.md` |
| Harness spec | `../.harness/spec/backend.md` |
| 当前 sprint | `../.harness/sprint_contracts/sprint_20260421_1.json` |
