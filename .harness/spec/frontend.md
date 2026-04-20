# SuperPipeline Frontend 开发规范

> 适用于 web/ 目录下所有代码

## 技术栈

- Next.js 15（App Router）
- TypeScript 5
- Tailwind CSS
- Shadcn/ui

## 代码组织

```
web/
├── src/
│   └── app/              # Next.js App Router
│       ├── page.tsx      # 首页
│       ├── pipeline/      # Pipeline 页面
│       └── layout.tsx    # 根布局
├── components/
│   ├── ui/               # Shadcn 组件
│   └── pipeline/          # Pipeline 业务组件
└── package.json
```

## 开发规范

### 组件规范

```tsx
// ✅ 正确：使用 TypeScript + Server Component
export default async function PipelinePage() {
  const data = await fetchPipelineData()
  return <PipelineView data={data} />
}

// ❌ 错误：不要用 any
function PipelinePage() {
  const data: any = fetchData()
  ...
}
```

### API 路由

```typescript
// ✅ 正确：使用 App Router Route Handlers
// app/api/pipeline/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const body = await req.json()
  const result = await runPipeline(body)
  return NextResponse.json(result)
}
```

### 状态管理

- 优先使用 React Server Components
- 客户端状态使用 `useState` / `useReducer`
- 避免不必要的 `use client`

### Tailwind CSS

- 使用 shadcn/ui 组件
- 避免自定义 CSS（优先用 Tailwind 工具类）
- 深色模式优先

## 文件命名

- 组件：PascalCase（如 `PipelineView.tsx`）
- 工具函数：camelCase（如 `usePipeline.ts`）
- 路由文件：`route.ts`

## Next.js 特定规范

### AGENTS.md

Next.js 项目有特殊的 AGENTS.md 头部：

```markdown
<!-- BEGIN:nextjs-agent-rules -->
<!-- END:nextjs-agent-rules -->
```

**不要修改这两行注释之间的内容**，这是 Claude Code 的 Next.js 规则注入点。

### 图片处理

- 使用 Next.js `<Image>` 组件
- 源文档图片使用原始 URL，不做额外压缩

### API 代理

前端调用后端统一通过 `/api/` 代理，不直接访问 server 的端口。

## AGENTS.md 位置

本目录的 AGENTS.md：`web/AGENTS.md`
