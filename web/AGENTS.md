<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

---

# SuperPipeline Web Generator 约束

> 本文件是三层架构的约束层落地，追加到 web/AGENTS.md

## Web 技术栈约束

- ✅ 使用 TypeScript，**禁止 any**
- ✅ 使用 App Router（app/ 目录），不要用 Pages Router
- ✅ 组件名：PascalCase（如 `PipelineView.tsx`）
- ✅ 工具函数名：camelCase（如 `usePipeline.ts`）
- ✅ 使用 Shadcn/ui 组件，不随意自定义 CSS
- ✅ API 路由放在 `app/api/` 下，使用 NextResponse

## Generator 职责

- 读取 `.harness/sprint_contracts/sprint_20260421_1.json` 获取当前任务
- 读取 `.harness/feature_list.json` 确认当前 feature 和 phase
- **禁止跳 phase**（phase=1 plan → phase=2 implement → phase=3 verify → phase=4 deliver）
- 完成后更新 feature_list.json 中的 phase
- 在 `.harness/eval_log.jsonl` 追加执行记录

## 当前 feature（phase=1）

- f001-2: Generator 约束落地（phase=1 plan）
