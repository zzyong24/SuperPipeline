# SuperPipeline UI Redesign Brief with shadcn/ui

**Status**: Analysis Complete ✓  
**Date**: 2026-04-15  
**Frontend**: Next.js 16.2.3 + React 19.2.4 + Tailwind CSS v4  
**Target**: Complete UI redesign using shadcn/ui components

---

## Executive Summary

The SuperPipeline web UI is a content production pipeline dashboard with:
- **3 main pages**: Dashboard, Content Library, Run Details
- **3 reusable components**: RunList, ContentCard, PipelineGraph
- **5 API endpoints** for runs and contents
- **Real-time support** via Server-Sent Events (not currently used)

The current UI uses vanilla Tailwind with basic styling. This document outlines the complete project structure and identifies opportunities for shadcn/ui integration.

---

## Quick Stats

| Metric | Value |
|--------|-------|
| **Total Pages** | 3 (Dashboard + Contents + Run Detail) |
| **Components** | 3 (RunList, ContentCard, PipelineGraph) |
| **API Endpoints** | 8 (runs, contents, pipelines, health, SSE) |
| **TypeScript Types** | 4 main interfaces |
| **Package Dependencies** | 9 (minimal, no UI libs) |
| **Current Bundle** | ~50-60kb gzipped |

---

## Project Structure at a Glance

```
SuperPipeline/
├── web/                          # Frontend (Next.js)
│   ├── src/
│   │   ├── app/                 # Pages & layouts
│   │   │   ├── page.tsx         # Dashboard (/)
│   │   │   ├── contents/
│   │   │   │   └── page.tsx     # Content library
│   │   │   ├── runs/[runId]/
│   │   │   │   └── page.tsx     # Run detail
│   │   │   ├── layout.tsx       # Root layout
│   │   │   └── globals.css      # Theme
│   │   ├── components/          # Reusable components
│   │   │   ├── RunList.tsx      # List of pipeline runs
│   │   │   ├── ContentCard.tsx  # Individual content card
│   │   │   └── PipelineGraph.tsx # Pipeline flow viz
│   │   └── lib/
│   │       ├── api-client.ts    # API wrapper (5 methods)
│   │       └── types.ts         # TypeScript definitions
│   └── package.json
│
└── server/                       # Backend (FastAPI)
    ├── src/api/
    │   ├── app.py              # FastAPI setup
    │   ├── routes/
    │   │   ├── runs.py         # Run endpoints
    │   │   ├── contents.py     # Content endpoints
    │   │   └── pipelines.py    # Pipeline endpoints
    │   ├── sse.py              # Server-Sent Events
    │   └── schemas.py          # Request schemas
    └── src/storage/
        ├── state_store.py      # SQLite storage
        └── models.py           # DB models & statuses
```

---

## Current Pages

### 1. Dashboard (`/`)
- **Fetches**: `GET /api/runs`
- **Shows**: Recent pipeline runs with status badges
- **Component**: `RunList`
- **Features**: Loading/error states

### 2. Content Library (`/contents`)
- **Fetches**: `GET /api/contents`
- **Filters**: Status (All, Approved, Pending Review, Published)
- **Component**: `ContentCard` (repeated)
- **Features**: Status toggle buttons, copy to clipboard

### 3. Run Detail (`/runs/[runId]`)
- **Fetches**: 
  - `GET /api/runs/{runId}` (metadata + state)
  - `GET /api/contents?run_id={runId}` (generated content)
- **Shows**: 
  - Pipeline flow (5 stages)
  - Selected topic
  - Generated content per platform
  - Review results per platform
  - Analysis & insights
  - Error log
- **Components**: `PipelineGraph`, `ContentCard`

---

## API Specification

### Runs Endpoints

```
GET /api/runs
  ├─ Query: limit=20, status=?
  └─ Returns: PipelineRun[]

GET /api/runs/{run_id}
  └─ Returns: PipelineRun with state object
```

### Contents Endpoints

```
GET /api/contents
  ├─ Query: status=?, run_id=?
  └─ Returns: Content[]

GET /api/contents/{content_id}
  └─ Returns: Content

POST /api/contents/{content_id}/approve
  ├─ Body: {publish_url?: string}
  └─ Returns: {message, content_id}
```

### Real-time Events (SSE)

```
GET /api/runs/{run_id}/events
  ├─ Type: EventSource (streaming)
  ├─ Events:
  │  ├─ stage_started
  │  ├─ stage_completed
  │  ├─ stage_failed
  │  └─ pipeline_completed
  └─ Closes after: pipeline_completed
```

---

## TypeScript Interfaces

### PipelineRun
```typescript
{
  run_id: string;
  pipeline_name: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;           // ISO timestamp
  updated_at: string;
  
  // Full state object in GET detail:
  state?: {
    topics?: [{title, angle, score}, ...];
    selected_topic?: {title, angle, score};
    materials?: any[];
    contents?: {[platform]: ContentData};
    reviews?: {[platform]: {score, passed, issues[]}};
    analysis?: {summary, insights[], improvement_suggestions[]};
    errors?: [{agent, message}, ...];
  }
}
```

### Content
```typescript
{
  content_id: string;
  run_id: string;
  platform: string;             // "xiaohongshu", "twitter", etc.
  title: string;
  body: string;
  tags: string[];
  status: "pending_review" | "approved" | "rejected" | "published";
  created_at: string;
  publish_url?: string;         // Added after approval
}
```

### PipelineEvent (for SSE)
```typescript
{
  type: "stage_started" | "stage_completed" | "stage_failed" | "pipeline_completed";
  agent?: string;
  timestamp: string;
  output_summary?: string;
  error?: string;
}
```

---

## Current Components

### RunList
- **Input**: `runs: Run[]`
- **Output**: List of clickable run cards with status
- **Features**: Status color-coding, formatted timestamps
- **Status Colors**: green-100/800, blue-100/800, red-100/800, gray-100/800

### ContentCard
- **Input**: `content: Content` object
- **Output**: Card with title, platform badge, body preview, tags, copy button
- **Features**: 
  - Copy to clipboard (shows "✓ Copied" for 2s)
  - 6-line body clamp
  - Platform badge
  - Tag formatting with #

### PipelineGraph
- **Input**: `stages: Stage[]`
- **Output**: Horizontal flow diagram with status icons
- **Features**: 
  - Status icons (⏳🔄✅❌)
  - Colored borders per status
  - Responsive horizontal scroll
  - Arrows between stages

---

## Styling & Design System

### Color Palette
```
Status Badges:
  ✅ completed → bg-green-100 text-green-800
  🔄 running   → bg-blue-100 text-blue-800
  ❌ failed    → bg-red-100 text-red-800
  ⏳ pending   → bg-gray-100 text-gray-800

Primary Actions:
  bg-gray-900 text-white (dark buttons)

Text:
  Headers → text-gray-900
  Secondary → text-gray-600
  Links → text-blue-600
  Muted → text-gray-400
```

### Layout
```
Container: max-w-4xl mx-auto p-6
Spacing: mb-4, mb-6, mb-8, gap-2, gap-4
Rounded: rounded, rounded-lg, rounded-full
```

### Theme Variables
```css
Light: --background: #fff, --foreground: #171717
Dark: --background: #0a0a0a, --foreground: #ededed
Font: Arial, Helvetica, sans-serif (system fonts)
```

---

## Missing Features (Redesign Opportunities)

### UI/UX Gaps
- ❌ No shadcn/ui components
- ❌ No loading skeletons
- ❌ No modal dialogs
- ❌ No table component for runs
- ❌ No error boundaries
- ❌ No advanced search/filtering
- ❌ No dark mode toggle UI

### Functionality Gaps
- ❌ No SSE integration (EventSource hook)
- ❌ No data caching (React Query/SWR)
- ❌ No content creation UI
- ❌ No authentication/authorization
- ❌ No notifications/toasts
- ❌ No offline support

### Architecture Gaps
- ❌ No Provider pattern (API context)
- ❌ No Server Components
- ❌ No error tracking/logging
- ❌ No tests (Jest/Vitest)
- ❌ No loading states with skeletons

---

## shadcn/ui Component Mapping

| Current | Target | Purpose |
|---------|--------|---------|
| Inline badge | `Badge` | Status indicators |
| `<button>` styled | `Button` | Primary actions |
| `<div>` with border | `Card` | Containers |
| Status buttons | `Tabs` or `ToggleGroup` | Filtering |
| — | `Dialog` | Content approval modal |
| Error text | `Alert` | Error display |
| "Loading..." text | `Skeleton` | Loading states |
| — | `Select` | Dropdown filters |
| — | `Input` | Search box |
| — | `Progress` | Stage progress |
| — | `Loader` | Spinner |
| RunList cards | `Table` | Alternative for run list |
| — | `Toast` | Notifications |
| — | `Tooltip` | Help text |

---

## Key Architecture Insights

### Current Data Flow
```
Page Component
  ├─ useEffect on mount
  ├─ api.listRuns() / api.listContents()
  ├─ Manual loading/error state
  └─ Render with data
```

### Recommended Architecture (post-redesign)
```
<ApiProvider>
  <ErrorBoundary>
    <DarkModeProvider>
      <Page>
        ├─ useQuery('runs', api.listRuns)  // React Query
        ├─ useRunEvents(runId)            // SSE hook
        └─ Render with state
```

---

## Implementation Roadmap

### Phase 1: Foundation (shadcn/ui Setup)
- [ ] Install shadcn/ui CLI
- [ ] Add core components (Button, Card, Badge)
- [ ] Update globals.css for shadcn theme
- [ ] Replace basic components incrementally

### Phase 2: UX Improvements
- [ ] Add loading skeletons
- [ ] Add error boundaries
- [ ] Replace filter buttons with Tabs
- [ ] Add dark mode toggle

### Phase 3: Advanced Features
- [ ] Integrate React Query
- [ ] Add SSE/EventSource hook
- [ ] Build content approval dialog
- [ ] Add advanced filtering with Select/Input

### Phase 4: Polish & Testing
- [ ] Add animations/transitions
- [ ] Performance optimization
- [ ] Accessibility audit (ARIA)
- [ ] Add E2E tests

---

## Critical Files for Development

### Frontend Files to Start With
- `/web/src/lib/types.ts` — Type definitions (start here)
- `/web/src/lib/api-client.ts` — API integration
- `/web/src/app/page.tsx` — Dashboard template
- `/web/src/app/globals.css` — Theme foundation
- `/web/src/components/RunList.tsx` — Component example

### Backend Files for Reference
- `/server/src/api/routes/runs.py` — Run endpoints
- `/server/src/api/routes/contents.py` — Content endpoints
- `/server/src/api/sse.py` — Real-time events
- `/server/src/storage/models.py` — Status constants

---

## Environment Setup

```bash
# Frontend
cd web
npm install
npm run dev              # http://localhost:3000

# Backend (from server directory)
python -m uvicorn src.api.app:create_app --reload
# API runs on http://localhost:8000
```

### Environment Variables
```bash
# .env.local (frontend)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Additional Notes

1. **Next.js Version**: Latest (16.2.3) with React Compiler
2. **TypeScript**: Strict mode enabled (good foundation)
3. **Tailwind v4**: Uses new `@theme` syntax, no tailwind.config.js needed
4. **No Custom Fonts**: Currently using system fonts (Arial)
5. **SSE Not Implemented**: EventSource not used in UI yet
6. **No State Management**: Using local useState only
7. **Minimal Dependencies**: Good starting point for adding shadcn/ui

---

## Quick Reference: API Response Examples

### GET /api/runs (list)
```json
[
  {
    "run_id": "run_abc123",
    "pipeline_name": "content_prod",
    "status": "running",
    "created_at": "2026-04-15T10:30:00Z",
    "updated_at": "2026-04-15T10:35:00Z"
  }
]
```

### GET /api/runs/{run_id} (detail)
```json
{
  "run_id": "run_abc123",
  "pipeline_name": "content_prod",
  "status": "completed",
  "created_at": "2026-04-15T10:30:00Z",
  "updated_at": "2026-04-15T11:30:00Z",
  "state": {
    "topics": [
      {"title": "AI in 2026", "angle": "future", "score": 0.95}
    ],
    "selected_topic": {"title": "AI in 2026", "angle": "future", "score": 0.95},
    "contents": {
      "xiaohongshu": {"title": "...", "body": "...", "tags": []},
      "twitter": {"title": "...", "body": "...", "tags": []}
    },
    "reviews": {
      "xiaohongshu": {"score": 0.9, "passed": true, "issues": []},
      "twitter": {"score": 0.85, "passed": true, "issues": []}
    },
    "analysis": {
      "summary": "Content performed well",
      "insights": ["High engagement"],
      "improvement_suggestions": ["Add more visuals"]
    }
  }
}
```

### GET /api/contents (list)
```json
[
  {
    "content_id": "content_xyz",
    "run_id": "run_abc123",
    "platform": "xiaohongshu",
    "title": "AI in 2026",
    "body": "...",
    "tags": ["ai", "future", "tech"],
    "status": "pending_review",
    "created_at": "2026-04-15T10:35:00Z"
  }
]
```

---

**End of UI Redesign Brief**

For detailed information, see: `EXPLORATION.md`
