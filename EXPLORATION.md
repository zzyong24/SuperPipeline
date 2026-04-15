# SuperPipeline Web UI & Backend API - Complete Project Exploration

**Date**: 2026-04-15  
**Purpose**: Comprehensive analysis for UI redesign using shadcn/ui  
**Frontend**: Next.js 16.2.3 + React 19.2.4 + Tailwind CSS v4  
**Backend**: FastAPI + SQLite storage

---

## 1. FRONTEND DIRECTORY STRUCTURE & FILES

### Complete File Tree
```
/web/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout + metadata
│   │   ├── page.tsx             # Dashboard page (/)
│   │   ├── globals.css          # Global Tailwind + theme
│   │   ├── favicon.ico
│   │   ├── contents/
│   │   │   └── page.tsx         # Content library (/contents)
│   │   └── runs/
│   │       └── [runId]/
│   │           └── page.tsx     # Run detail (/runs/:runId)
│   ├── components/
│   │   ├── RunList.tsx          # Renders list of runs
│   │   ├── ContentCard.tsx      # Single content display
│   │   └── PipelineGraph.tsx    # Pipeline flow visualization
│   └── lib/
│       ├── api-client.ts        # Fetch wrapper for all API calls
│       └── types.ts             # TypeScript interfaces
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
└── README.md
```

---

## 2. NEXT.JS & BUILD CONFIGURATION

### package.json Dependencies
```json
{
  "next": "16.2.3",           // Latest Next.js
  "react": "19.2.4",          // Latest React with React Compiler
  "react-dom": "19.2.4",
  "tailwindcss": "^4",        // v4 (new @theme syntax)
  "@tailwindcss/postcss": "^4",
  "typescript": "^5",
  "@types/react": "^19",
  "@types/react-dom": "^19",
  "@types/node": "^20"
}
```

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "strict": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "paths": {
      "@/*": ["./src/*"]  // Alias for imports
    }
  },
  "include": ["**/*.ts", "**/*.tsx", ".next/types/**/*.ts"]
}
```

### next.config.ts
```typescript
import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  /* config options here */
};
export default nextConfig;
```
*Currently empty - no special routing, redirects, or middleware*

### postcss.config.mjs
```javascript
const config = {
  plugins: {
    "@tailwindcss/postcss": {},  // Tailwind v4 uses new PostCSS plugin
  },
};
export default config;
```

---

## 3. GLOBAL STYLING & THEME (globals.css)

```css
@import "tailwindcss";

:root {
  --background: #ffffff;      /* Light mode background */
  --foreground: #171717;      /* Light mode text */
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: var(--font-geist-sans);    /* Unused - falls back to Arial */
  --font-mono: var(--font-geist-mono);
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;      /* Dark mode background */
    --foreground: #ededed;      /* Dark mode text */
  }
}

body {
  background: var(--background);
  color: var(--foreground);
  font-family: Arial, Helvetica, sans-serif;  /* No custom fonts */
}
```

**Current Palette:**
- Light: White bg (#fff) + Dark gray text (#171717)
- Dark: Almost black bg (#0a0a0a) + Light gray text (#ededed)
- No custom colors defined - uses default Tailwind palette

---

## 4. TYPESCRIPT TYPES (lib/types.ts)

### Core Domain Models

```typescript
export interface PipelineRun {
  run_id: string;                    // Unique identifier
  pipeline_name: string;             // Name of the pipeline config
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;                // ISO 8601 timestamp
  updated_at: string;                // ISO 8601 timestamp
  
  // Additional fields from state (in GET detail response):
  state?: {
    topics?: Array<{title: string; angle: string; score: number}>;
    selected_topic?: {title: string; angle: string; score: number};
    materials?: any[];
    contents?: Record<string, any>;  // platform -> content
    reviews?: Record<string, {score: number; passed: boolean; issues: string[]}>;
    analysis?: {
      summary: string;
      insights: string[];
      improvement_suggestions: string[];
    };
    errors?: Array<{agent: string; message: string}>;
  };
}

export interface Content {
  content_id: string;
  run_id: string;                    // Links to PipelineRun
  platform: string;                  // e.g., "xiaohongshu", "twitter"
  title: string;
  body: string;
  tags: string[];                    // Array of hashtags
  status: "pending_review" | "approved" | "rejected" | "published";
  created_at: string;                // ISO 8601
  
  // Additional fields from approveContent:
  publish_url?: string;
}

export interface PipelineStage {
  agent: string;                     // Agent name (topic_generator, etc.)
  status: "pending" | "running" | "completed" | "failed";
  output_summary?: string;           // Optional summary
}

export interface PipelineEvent {
  type: "stage_started" | "stage_completed" | "stage_failed" | "pipeline_completed";
  agent?: string;
  timestamp: string;
  output_summary?: string;
  error?: string;
}
```

---

## 5. API CLIENT (lib/api-client.ts)

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T>
  // Generic fetch wrapper with JSON content-type

export const api = {
  // Runs
  listRuns(): Promise<PipelineRun[]>
    // GET /api/runs?limit=20&status=...
  getRun(runId: string): Promise<PipelineRun>
    // GET /api/runs/{runId}

  // Contents
  listContents(params?: {status?: string; run_id?: string}): Promise<Content[]>
    // GET /api/contents?status=approved&run_id=xyz
  getContent(id: string): Promise<Content>
    // GET /api/contents/{id}
  approveContent(id: string, publishUrl?: string): Promise<{message: string; content_id: string}>
    // POST /api/contents/{id}/approve { publish_url: string }
};
```

**Environment Variable**: `NEXT_PUBLIC_API_URL` (client-side accessible)

---

## 6. PAGES

### Dashboard Page (app/page.tsx)

**Route**: `/`

**Features**:
- Displays "Recent Runs" section
- Navigation header with Dashboard/Contents links
- Uses RunList component
- Loading/error states with text only

**Data Flow**:
1. `useEffect` calls `api.listRuns()`
2. Sets `runs` state
3. Renders RunList or loading/error message

**Styling**: `max-w-4xl mx-auto p-6` container

---

### Contents Page (app/contents/page.tsx)

**Route**: `/contents`

**Features**:
- "Content Library" heading
- Filter buttons: "All", "Approved", "Pending Review", "Published"
- Toggle filter updates both filter state and resets loading
- Maps through contents array with ContentCard component
- Loading/error states

**Filter Logic**:
```typescript
const params = filter === "all" ? {} : { status: filter };
api.listContents(params).then(setContents);
```

**Styling**: Button toggle group with conditional classes:
- Active: `bg-gray-900 text-white border-gray-900`
- Inactive: `bg-white text-gray-600 border-gray-300`

---

### Run Detail Page (app/runs/[runId]/page.tsx)

**Route**: `/runs/[runId]`

**Sections Rendered**:
1. **Header**: Run ID, pipeline name, creation date, status badge
2. **Pipeline Stages**: Visualization with PipelineGraph
   - Pipeline stages: topic_generator → material_collector → content_generator → reviewer → analyst
   - Determines stage status based on errors and state data presence
3. **Selected Topic**: Shows title, angle, score, stats
4. **Generated Contents**: ContentCard for each content item
5. **Reviews**: Platform-specific review results with score/passed status
6. **Analysis**: Summary, insights, improvement suggestions
7. **Errors**: List of agent errors

**Data Fetching**:
```typescript
Promise.all([
  api.getRun(runId),
  api.listContents({ run_id: runId })
])
```

**Stage Status Logic**:
- Error exists → "failed"
- Data exists for stage → "completed"
- Otherwise → "pending"

---

## 7. COMPONENTS

### RunList Component

**Props**: `{runs: Run[]}`

**Renders**:
- For each run: clickable block with run_id (mono), pipeline_name, status badge
- Status colors: `green-100/800`, `blue-100/800`, `red-100/800`, `gray-100/800`
- Timestamp at bottom
- Links to `/runs/{run.run_id}`

---

### ContentCard Component

**Props**: 
```typescript
interface ContentCardProps {
  content: {
    content_id: string;
    platform: string;
    title: string;
    body: string;
    tags: string[];
    status: string;
  };
}
```

**Features**:
- Platform badge (blue background)
- Status text (small gray)
- Title (bold)
- Body (6-line clamp, whitespace-pre-wrap)
- Tags (formatted with #)
- Copy to Clipboard button (dark gray)
  - Shows "✓ Copied" for 2s after click
  - Copies: `${title}\n\n${body}\n\n#tag1 #tag2`

**Styling**: Border rounded card with spacing

---

### PipelineGraph Component

**Props**: `{stages: Stage[]}`

**Renders**:
- Horizontal flex container (scrollable)
- For each stage:
  - Colored box with status icon (⏳🔄✅❌)
  - Agent name below icon
  - Borders based on status (blue/green/red/gray)
- Arrow separator between stages (→)

**Stage Status Styling**:
- pending: `border-gray-300 bg-gray-50`
- running: `border-blue-500 bg-blue-50`
- completed: `border-green-500 bg-green-50`
- failed: `border-red-500 bg-red-50`

---

## 8. BACKEND API ENDPOINTS

### Runs API

**GET /api/runs**

Query Parameters:
- `limit`: integer (default: 20)
- `status`: string optional ("pending", "running", "completed", "failed")

Response: `PipelineRun[]`
```json
[
  {
    "run_id": "run_abc123",
    "pipeline_name": "content_prod",
    "status": "running",
    "created_at": "2026-04-15T10:30:00Z",
    "updated_at": "2026-04-15T10:35:00Z",
    "state": { /* full run state */ }
  }
]
```

---

**GET /api/runs/{run_id}**

Response: Single `PipelineRun` with full state object

State Structure:
```typescript
{
  topics?: [
    { title: string; angle: string; score: number }
  ];
  selected_topic?: { title: string; angle: string; score: number };
  materials?: any[];
  contents?: {
    [platform: string]: ContentData
  };
  reviews?: {
    [platform: string]: {
      score: number;
      passed: boolean;
      issues: string[];
    }
  };
  analysis?: {
    summary: string;
    insights: string[];
    improvement_suggestions: string[];
  };
  errors?: [
    { agent: string; message: string }
  ];
  stage?: string;
}
```

---

### Contents API

**GET /api/contents**

Query Parameters:
- `status`: optional ("pending_review", "approved", "rejected", "published")
- `run_id`: optional (filter by specific run)

Response: `Content[]`

---

**GET /api/contents/{content_id}**

Response: Single `Content`

---

**POST /api/contents/{content_id}/approve**

Request Body:
```json
{
  "publish_url": "https://example.com/post"  // Optional
}
```

Response:
```json
{
  "message": "Content marked as published",
  "content_id": "content_xyz"
}
```

Side Effects:
- Updates content status to "published"
- Stores publish_url if provided

---

### Pipelines API

**GET /api/pipelines**

Response: `Array<PipelineDefinition>`

Returns list of available pipeline configurations.

---

### Server-Sent Events (SSE)

**GET /api/runs/{run_id}/events**

Connection Type: **EventSource** (HTTP long-polling with Server-Sent Events)

Event Types Published:
1. **stage_started**: Agent started processing
2. **stage_completed**: Agent finished successfully
3. **stage_failed**: Agent error occurred
4. **pipeline_completed**: Entire pipeline finished
5. **keepalive**: Keep-alive ping every 30 seconds (if no data)

Event Data Structure:
```json
{
  "type": "stage_completed",
  "agent": "topic_generator",
  "timestamp": "2026-04-15T10:35:30Z",
  "output_summary": "Generated 5 topic ideas",
  "error": null
}
```

Connection Behavior:
- Stays open until `pipeline_completed` event
- Timeout: 30 seconds of inactivity
- HTTP status: 200 with `text/event-stream` content-type

---

### Health Check

**GET /health**

Response:
```json
{
  "status": "ok"
}
```

---

## 9. CURRENT UI STYLING & DESIGN SYSTEM

### Color Palette (Tailwind)

**Status Colors**:
- ✅ Completed: `bg-green-100 text-green-800`
- 🔄 Running: `bg-blue-100 text-blue-800`
- ❌ Failed: `bg-red-100 text-red-800`
- ⏳ Pending: `bg-gray-100 text-gray-800`

**Primary Actions**:
- Buttons: `bg-gray-900 text-white` with hover state

**Text Colors**:
- Headers: `text-gray-900`
- Secondary: `text-gray-600`
- Links: `text-blue-600`
- Muted: `text-gray-400`

**Borders**:
- Standard: `border border-gray-300`
- Active: `border-gray-900`

### Spacing & Layout

**Container**: 
- `max-w-4xl mx-auto p-6` (standard across all pages)

**Gaps & Spacing**:
- Section margin: `mb-4`, `mb-6`, `mb-8`
- Component gap: `gap-2`, `gap-4`
- Padding: `p-3`, `p-4`, `p-6`

**Rounded Corners**:
- `rounded` (standard)
- `rounded-lg` (large)
- `rounded-full` (pills)

**Typography**:
- Headers: `text-lg`, `text-xl`, `text-2xl` with `font-semibold` or `font-bold`
- Body: `text-sm`, default
- Mono: `font-mono text-sm` for IDs

---

## 10. CURRENT MISSING FEATURES & GAPS

### UI/UX Gaps
1. ❌ No shadcn/ui components - All custom Tailwind
2. ❌ No form components - Manual button toggles for filters
3. ❌ No loading states - "Loading..." text only, no skeletons
4. ❌ No error boundaries - Generic error messages
5. ❌ No modal dialogs - No content editing UI
6. ❌ No tables - Run list is using cards
7. ❌ No pagination UI - Uses API limit parameter only
8. ❌ No advanced search - Status filter only
9. ❌ No infinite scroll/virtualization

### Functionality Gaps
1. ❌ No SSE integration - EventSource not used
2. ❌ No real-time updates - Manual page refresh
3. ❌ No data caching - Fresh API calls each time
4. ❌ No offline support - No service worker
5. ❌ No content creation UI - Only viewing/approving
6. ❌ No authentication - No login/logout
7. ❌ No role-based access - No permissions system
8. ❌ No notifications - No toast/alert system

### Architecture Gaps
1. ❌ No Context/Provider pattern - API client exposed globally
2. ❌ No React Query/SWR - Manual fetch management
3. ❌ No Server Components - All client-side
4. ❌ No environment config UI - Only env variables
5. ❌ No error tracking - No logging service

---

## 11. DATABASE & STORAGE MODELS (Backend Reference)

### Content Status Values
```python
STATUS_PENDING_REVIEW = "pending_review"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_PUBLISHED = "published"
```

### Run Status Values
```python
RUN_STATUS_PENDING = "pending"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
```

### Storage Implementation
- **Database**: SQLite (via `StateStore`)
- **Assets**: File-based storage (via `AssetStore`)
- **Config**: YAML-based pipeline definitions

---

## 12. KEY INSIGHTS FOR SHADCN/UI REDESIGN

### Why Redesign with shadcn/ui?

1. **Better DX**: Pre-built, headless components
2. **Consistency**: Unified design system
3. **Accessibility**: Built-in a11y support (ARIA)
4. **Dark Mode**: Native dark mode support
5. **Customization**: Copy-paste approach allows tweaks
6. **Modern UX**: Animations, transitions, feedback
7. **Type Safety**: Full TypeScript support

### Component Migration Map

**Current → shadcn/ui**

| Current | Target Component | Use Case |
|---------|-----------------|----------|
| Status badge (inline) | `Badge` | Status indicators |
| Button.bg-gray-900 | `Button` | Primary actions |
| ContentCard border | `Card` | Content containers |
| RunList.space-y-2 | `Table` or `List` | Data lists |
| Filter buttons | `Tabs` or `ToggleGroup` | Status filtering |
| ----- | `Dialog` | Content approval modal |
| ----- | `AlertDialog` | Confirmation dialogs |
| Loading "..." text | `Skeleton` | Loading states |
| Error messages | `Alert` | Error display |
| ----- | `Select` | Dropdown filters |
| ----- | `Input` | Search/filter inputs |
| ----- | `Progress` | Pipeline progress |
| ----- | `Loader` | Spinner indicator |
| PipelineGraph | Custom | Complex viz (keep custom) |

### Architecture Improvements

1. **Add Data Provider**
   ```typescript
   // Create ApiProvider context
   const ApiContext = createContext<typeof api>(null);
   
   export function ApiProvider({ children }) {
     return <ApiContext.Provider value={api}>{children}</ApiContext.Provider>;
   }
   
   export const useApi = () => useContext(ApiContext);
   ```

2. **Add Query Management**
   ```typescript
   // Use React Query for data fetching
   import { useQuery } from '@tanstack/react-query';
   
   const { data: runs, isLoading } = useQuery({
     queryKey: ['runs'],
     queryFn: () => api.listRuns()
   });
   ```

3. **Add Real-time Support**
   ```typescript
   // SSE hook for real-time updates
   export const useRunEvents = (runId: string) => {
     const [events, setEvents] = useState<PipelineEvent[]>([]);
     
     useEffect(() => {
       const source = new EventSource(`/api/runs/${runId}/events`);
       source.onmessage = (e) => {
         setEvents(prev => [...prev, JSON.parse(e.data)]);
       };
       return () => source.close();
     }, [runId]);
     
     return events;
   };
   ```

4. **Error Boundary**
   ```typescript
   // Catch React errors
   export const ErrorBoundary = ({ children }) => {
     // Implement with react-error-boundary or custom
   };
   ```

### New Features to Enable

1. **Real-time Pipeline Monitoring**
   - SSE EventSource for live updates
   - Streaming stage progress
   - Auto-refresh run detail when complete

2. **Advanced Filtering & Search**
   - Full-text search across content
   - Multi-status filtering
   - Date range filters
   - Platform/tag filtering

3. **Content Management**
   - Inline content approval/rejection
   - Edit content before approval
   - Bulk actions (approve multiple)
   - Custom publish URL input

4. **Dashboard Enhancements**
   - Statistics cards (total runs, success rate, etc.)
   - Recent activity feed
   - Pipeline status at a glance
   - Run creation form

5. **Dark Mode**
   - Toggle in header
   - Persistent preference
   - Respects system preference

---

## 13. DEPLOYMENT & CONFIGURATION

### Environment Variables (Frontend)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Set in `.env.local` or deployment platform.

### Build & Run Commands

```bash
npm run dev      # Development (http://localhost:3000)
npm run build    # Production build
npm start        # Production server
```

### Next.js Features in Use

- ✅ App Router (`/app` directory)
- ✅ Client Components (`"use client"`)
- ✅ TypeScript strict mode
- ✅ Path aliases (`@/*`)
- ❌ Server Components (not used)
- ❌ API Routes (backend separate)
- ❌ Middleware (no authentication middleware)

---

## 14. FILE SIZE & DEPENDENCIES ANALYSIS

### Bundle Analysis

**Current Dependencies**:
- `next`: 16.2.3
- `react`: 19.2.4
- `react-dom`: 19.2.4
- `tailwindcss`: ^4
- Build tools (TypeScript, PostCSS, etc.)

**New Dependencies for Redesign**:
- `@radix-ui/*`: ~15-20 core packages
- `class-variance-authority`: ~5kb
- `clsx`: ~2kb
- `@tanstack/react-query`: ~30kb (optional, for data fetching)

**Total Impact**: ~150-200kb added to bundle (gzipped)

---

## 15. TESTING & VALIDATION

### No Tests Currently Implemented

- ❌ No Jest/Vitest setup
- ❌ No React Testing Library tests
- ❌ No E2E tests (Cypress/Playwright)
- ❌ No API mocking (MSW)

**Recommendations for Full Redesign**:
1. Add Vitest for unit tests
2. Add React Testing Library for component tests
3. Add Playwright for E2E tests
4. Mock API with MSW for testing

---

## 16. PERFORMANCE METRICS

### Current State

- **Pages**: 3 dynamic routes
- **Components**: 3 reusable components
- **API Calls**: 5 main endpoints
- **Bundle Size**: ~50-60kb (gzipped, with deps)

### Optimization Opportunities

1. **Image Optimization**: Use `next/image` (currently none)
2. **Code Splitting**: Already done by Next.js
3. **Caching**: Add SWR/React Query cache strategy
4. **Preloading**: Prefetch navigation links
5. **Streaming**: Use Suspense for streaming responses

---

## 17. QUICK START FOR REDESIGN IMPLEMENTATION

### Phase 1: Foundation
1. Install shadcn/ui
2. Add core components (Button, Card, Badge, Alert)
3. Update globals.css to match shadcn palette
4. Replace existing components one by one

### Phase 2: UX Improvements
1. Add loading skeletons
2. Add error boundaries
3. Improve form components
4. Add dark mode toggle

### Phase 3: Advanced Features
1. Integrate React Query
2. Add SSE/EventSource for real-time
3. Add advanced filtering
4. Content approval modal

### Phase 4: Polish
1. Add animations
2. Optimize performance
3. Add analytics
4. Accessibility audit

---

## 18. CRITICAL FILES FOR REFERENCE

**Frontend**:
- `/web/src/lib/api-client.ts` - All API calls start here
- `/web/src/lib/types.ts` - Type definitions
- `/web/src/app/page.tsx` - Dashboard template
- `/web/src/components/ContentCard.tsx` - Component example
- `/web/src/app/globals.css` - Theme foundation

**Backend**:
- `/server/src/api/app.py` - FastAPI setup
- `/server/src/api/routes/runs.py` - Run endpoints
- `/server/src/api/routes/contents.py` - Content endpoints
- `/server/src/api/sse.py` - Real-time events
- `/server/src/api/schemas.py` - Request/response models

---

**END OF EXPLORATION DOCUMENT**
