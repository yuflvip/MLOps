# MLOps Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Vue 3 + Element Plus frontend for the MLOps backend, covering training task management, template browsing, and ONNX model conversion.

**Architecture:** Modular SPA with feature-based module organization under `src/modules/`. Shared infrastructure in `src/shared/`. Dark sci-fi theme based on TrafficMind reference. API calls via Axios with Vite proxy in development.

**Tech Stack:** Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue Router 4, Axios, pnpm

**Design Spec:** `docs/superpowers/specs/2026-06-08-mlops-frontend-design.md`

---

## File Map

### Configuration (root)
- `frontend/package.json` — dependencies & scripts
- `frontend/vite.config.ts` — build config, proxy, aliases
- `frontend/tsconfig.json` — TS root config
- `frontend/tsconfig.app.json` — TS app config
- `frontend/tsconfig.node.json` — TS node config
- `frontend/env.d.ts` — env type declarations
- `frontend/.env.development` — dev environment variables
- `frontend/index.html` — HTML entry

### Styles
- `frontend/src/styles/variables.scss` — CSS variables overriding Element Plus
- `frontend/src/styles/dark-overrides.scss` — Element Plus component dark overrides
- `frontend/src/styles/global.scss` — body background, grid, scrollbar, fonts
- `frontend/src/styles/theme.css` — TrafficMind-style custom effects

### Shared Layer
- `frontend/src/shared/types/index.ts` — PaginationParams, PaginatedData
- `frontend/src/shared/api/types.ts` — ApiEnvelope, ApiError
- `frontend/src/shared/api/client.ts` — Axios instance + interceptors
- `frontend/src/shared/api/modules/training.ts` — training API calls
- `frontend/src/shared/api/modules/conversion.ts` — conversion API calls
- `frontend/src/shared/api/modules/system.ts` — system API calls
- `frontend/src/shared/utils/format.ts` — formatTime, formatBytes
- `frontend/src/shared/utils/constants.ts` — TASK_STATUS_MAP, TASK_STATUS_COLORS
- `frontend/src/shared/composables/usePagination.ts` — pagination state logic
- `frontend/src/shared/composables/useLoading.ts` — loading wrapper
- `frontend/src/shared/stores/app.ts` — sidebar collapse state
- `frontend/src/shared/components/PageHeader.vue` — page title bar
- `frontend/src/shared/components/JsonViewer.vue` — JSON tree display
- `frontend/src/shared/components/StatusTag.vue` — colored status badge
- `frontend/src/shared/components/EmptyState.vue` — empty data placeholder
- `frontend/src/shared/components/PlaceholderPage.vue` — "coming soon" page

### App Layer
- `frontend/src/main.ts` — app bootstrap
- `frontend/src/App.vue` — root component
- `frontend/src/app/router/index.ts` — route definitions
- `frontend/src/app/layouts/MainLayout.vue` — header + sidebar + main grid
- `frontend/src/app/layouts/AppHeader.vue` — top bar
- `frontend/src/app/layouts/AppSidebar.vue` — navigation sidebar

### Training Module
- `frontend/src/modules/training/types/index.ts` — TrainingTask, TrainingDetail, CreateMeta, etc.
- `frontend/src/modules/training/stores/training.ts` — Pinia store
- `frontend/src/modules/training/composables/useTrainingList.ts` — list page logic
- `frontend/src/modules/training/routes.ts` — module routes
- `frontend/src/modules/training/index.ts` — module exports
- `frontend/src/modules/training/components/TaskStatusTag.vue` — status tag
- `frontend/src/modules/training/components/TaskListPage.vue` — task list page
- `frontend/src/modules/training/components/CreateTaskDrawer.vue` — create task drawer
- `frontend/src/modules/training/components/TaskDetailPage.vue` — task detail page
- `frontend/src/modules/training/components/ConversionDrawer.vue` — ONNX export drawer

### Template Module
- `frontend/src/modules/template/types/index.ts` — TemplateItem, QueueStatusItem
- `frontend/src/modules/template/stores/template.ts` — Pinia store
- `frontend/src/modules/template/composables/useTemplates.ts` — template loading logic
- `frontend/src/modules/template/routes.ts` — module routes
- `frontend/src/modules/template/index.ts` — module exports
- `frontend/src/modules/template/components/TemplateCard.vue` — template card
- `frontend/src/modules/template/components/TemplateDetailDialog.vue` — detail dialog
- `frontend/src/modules/template/components/TemplateListPage.vue` — template list page

### Placeholder Modules
- `frontend/src/modules/model-registry/types/index.ts` — future types
- `frontend/src/modules/model-registry/routes.ts` — placeholder route
- `frontend/src/modules/model-registry/index.ts` — exports
- `frontend/src/modules/auth/types/index.ts` — future types
- `frontend/src/modules/auth/routes.ts` — placeholder route
- `frontend/src/modules/auth/index.ts` — exports

---

## Task 1: Project Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/env.d.ts`
- Create: `frontend/.env.development`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`

- [ ] **Step 1: Create project with Vite**

```bash
cd /mnt/d/workspace-2026/MLOps
pnpm create vite frontend --template vue-ts
cd frontend
```

- [ ] **Step 2: Install dependencies**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm install
pnpm add element-plus @element-plus/icons-vue axios pinia vue-router@4
pnpm add -D sass unplugin-auto-import unplugin-vue-components @types/node
```

- [ ] **Step 3: Configure vite.config.ts**

Replace `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver({ importStyle: 'sass' })],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables.scss" as *;`,
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:18087',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: Configure tsconfig.app.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForExpose": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue", "env.d.ts"]
}
```

- [ ] **Step 5: Create env files**

Create `frontend/.env.development`:

```
VITE_API_BASE_URL=/api
```

Create `frontend/env.d.ts`:

```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

- [ ] **Step 6: Update index.html title**

Replace `frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>MLOps Platform</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 7: Create placeholder main.ts**

Replace `frontend/src/main.ts`:

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/theme-chalk/src/index.scss'
import '@/styles/global.scss'
import '@/styles/dark-overrides.scss'
import '@/styles/theme.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 8: Create placeholder App.vue**

Replace `frontend/src/App.vue`:

```vue
<template>
  <div class="app-root">MLOps Frontend</div>
</template>
```

- [ ] **Step 9: Verify dev server starts**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm dev
```

Expected: Dev server starts on http://localhost:3000, page shows "MLOps Frontend". Press Ctrl+C to stop.

- [ ] **Step 10: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/
git commit -m "feat(frontend): scaffold Vue 3 + TypeScript + Vite project"
```

---

## Task 2: Theme & Global Styles

**Files:**
- Create: `frontend/src/styles/variables.scss`
- Create: `frontend/src/styles/dark-overrides.scss`
- Create: `frontend/src/styles/global.scss`
- Create: `frontend/src/styles/theme.css`

- [ ] **Step 1: Create variables.scss**

Create `frontend/src/styles/variables.scss`:

```scss
// TrafficMind-inspired dark theme color system
// Override Element Plus CSS variables

// Background
$--bg:          #070e22;
$--bg2:         #0b1730;
$--panel:       #0e1d3d;
$--panel2:      #122448;

// Border
$--line:        rgba(80, 140, 255, 0.18);
$--line2:       rgba(80, 140, 255, 0.35);

// Text
$--txt:         #dbe6ff;
$--txt2:        #8aa0cc;
$--muted:       #5f739c;

// Accent
$--cyan:        #28e0e0;
$--blue:        #3b82f6;
$--teal:        #22d3ee;

// Functional
$--green:       #36e08a;
$--amber:       #ffb020;
$--red:         #ff5a6e;
$--purple:      #9b7bff;

// Glow
$--glow:        0 0 18px rgba(40, 224, 224, 0.25);

// Scrollbar
$--scroll-track:   rgba(3, 12, 28, 0.42);
$--scroll-thumb:   rgba(95, 115, 156, 0.42);
$--scroll-hover:   rgba(40, 224, 224, 0.52);

// Font
$--font-family:    "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
$--font-mono:      Consolas, "Courier New", monospace;

// Element Plus variable overrides
$--el-color-primary: $--blue;
$--el-color-success: $--green;
$--el-color-warning: $--amber;
$--el-color-danger:  $--red;

// Forward as CSS custom properties for runtime use
:root {
  --bg: #{$--bg};
  --bg2: #{$--bg2};
  --panel: #{$--panel};
  --panel2: #{$--panel2};
  --line: #{$--line};
  --line2: #{$--line2};
  --txt: #{$--txt};
  --txt2: #{$--txt2};
  --muted: #{$--muted};
  --cyan: #{$--cyan};
  --blue: #{$--blue};
  --teal: #{$--teal};
  --green: #{$--green};
  --amber: #{$--amber};
  --red: #{$--red};
  --purple: #{$--purple};
  --glow: #{$--glow};

  --el-bg-color: #{$--bg};
  --el-bg-color-page: #{$--bg2};
  --el-bg-color-overlay: #{$--panel};
  --el-border-color: #{$--line};
  --el-border-color-light: #{$--line};
  --el-border-color-lighter: #{$--line};
  --el-border-color-extra-light: #{$--line};
  --el-text-color-primary: #{$--txt};
  --el-text-color-regular: #{$--txt2};
  --el-text-color-secondary: #{$--muted};
  --el-text-color-placeholder: #{$--muted};
  --el-fill-color: #{$--panel};
  --el-fill-color-light: #{$--panel2};
  --el-fill-color-lighter: #{$--panel};
  --el-fill-color-blank: #{$--bg2};
  --el-mask-color: rgba(0, 0, 0, 0.6);
}
```

- [ ] **Step 2: Create dark-overrides.scss**

Create `frontend/src/styles/dark-overrides.scss`:

```scss
// Element Plus component overrides for dark theme

// Input
.el-input__wrapper {
  background-color: #08152e;
  box-shadow: 0 0 0 1px var(--line2) inset;
}
.el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--line2) inset;
}
.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--cyan) inset;
}

// Select dropdown
.el-select-dropdown {
  background-color: var(--panel);
  border-color: var(--line2);
}
.el-select-dropdown__item.is-hovering {
  background-color: var(--panel2);
}
.el-select-dropdown__item.is-selected {
  color: var(--cyan);
}

// Table
.el-table {
  --el-table-bg-color: var(--panel);
  --el-table-tr-bg-color: var(--panel);
  --el-table-header-bg-color: var(--panel2);
  --el-table-row-hover-bg-color: rgba(40, 224, 224, 0.06);
  --el-table-border-color: var(--line);
  --el-table-text-color: var(--txt);
  --el-table-header-text-color: var(--txt2);
}

// Card
.el-card {
  background: linear-gradient(180deg, var(--panel), rgba(10, 22, 48, 0.6));
  border-color: var(--line);
  border-radius: 14px;
}

// Dialog
.el-dialog {
  background-color: var(--panel);
  border: 1px solid var(--line2);
  border-radius: 14px;
}
.el-dialog__header {
  border-bottom: 1px solid var(--line);
}
.el-dialog__title {
  color: var(--txt);
}

// Drawer
.el-drawer {
  background-color: var(--panel);
}
.el-drawer__header {
  color: var(--txt);
  border-bottom: 1px solid var(--line);
  margin-bottom: 0;
  padding-bottom: 16px;
}

// Pagination
.el-pagination {
  --el-pagination-bg-color: transparent;
  --el-pagination-button-bg-color: var(--panel2);
  --el-pagination-hover-color: var(--cyan);
}
.el-pager li {
  background-color: var(--panel2) !important;
  color: var(--txt2) !important;
}
.el-pager li.is-active {
  background-color: var(--blue) !important;
  color: #fff !important;
}

// Button primary glow
.el-button--primary {
  background: linear-gradient(90deg, var(--blue), var(--teal));
  border-color: transparent;
  color: #04122e;
  font-weight: 700;
}
.el-button--primary:hover {
  filter: brightness(1.1);
  border-color: transparent;
  color: #04122e;
}

// Tag
.el-tag {
  border-radius: 6px;
}

// Loading overlay
.el-loading-mask {
  background-color: rgba(7, 14, 34, 0.7);
}

// Message
.el-message {
  background-color: var(--panel2);
  border-color: var(--line2);
}

// Form item label
.el-form-item__label {
  color: var(--txt2);
}

// Tabs
.el-tabs__item.is-active {
  color: var(--cyan);
}
.el-tabs__active-bar {
  background-color: var(--cyan);
}

// Descriptions
.el-descriptions {
  --el-descriptions-table-border: var(--line);
}
.el-descriptions__label {
  color: var(--txt2) !important;
  background-color: var(--panel2) !important;
}
.el-descriptions__content {
  color: var(--txt) !important;
  background-color: var(--panel) !important;
}
```

- [ ] **Step 3: Create global.scss**

Create `frontend/src/styles/global.scss`:

```scss
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body, #app {
  height: 100%;
}

body {
  font-family: $--font-family;
  background: radial-gradient(1200px 800px at 70% -10%, #13284f 0%, $--bg 55%) fixed, $--bg;
  color: $--txt;
  overflow: hidden;
}

// Grid overlay
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image:
    linear-gradient(rgba(80, 140, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(80, 140, 255, 0.04) 1px, transparent 1px);
  background-size: 46px 46px;
}

#app {
  position: relative;
  z-index: 1;
}

// Scrollbar
* {
  scrollbar-width: thin;
  scrollbar-color: $--scroll-thumb $--scroll-track;
}

::-webkit-scrollbar {
  width: 9px;
  height: 9px;
}
::-webkit-scrollbar-track {
  background: $--scroll-track;
  border-radius: 10px;
}
::-webkit-scrollbar-thumb {
  background: $--scroll-thumb;
  border: 2px solid transparent;
  border-radius: 10px;
  background-clip: padding-box;
}
::-webkit-scrollbar-thumb:hover {
  background: $--scroll-hover;
  border: 2px solid transparent;
  background-clip: padding-box;
}

// Utility classes
.font-mono {
  font-family: $--font-mono;
}

.text-cyan {
  color: $--cyan;
}

.text-muted {
  color: $--muted;
}

.text-secondary {
  color: $--txt2;
}
```

- [ ] **Step 4: Create theme.css**

Create `frontend/src/styles/theme.css`:

```css
/* Custom TrafficMind-style effects that don't fit in SCSS variables */

/* Card glow dot */
.card-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--cyan);
  box-shadow: var(--glow);
  display: inline-block;
  margin-right: 8px;
}

/* Page heading cyan bar */
.page-bar {
  display: inline-block;
  width: 5px;
  height: 20px;
  background: var(--cyan);
  border-radius: 3px;
  margin-right: 10px;
  vertical-align: -2px;
  box-shadow: var(--glow);
}

/* Glow card hover */
.glow-card {
  transition: border-color 0.18s, box-shadow 0.18s;
}
.glow-card:hover {
  border-color: var(--cyan) !important;
  box-shadow: var(--glow) !important;
}

/* Fade-in animation */
.fade-enter-active {
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
```

- [ ] **Step 5: Verify styles compile**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm dev
```

Expected: Dev server starts without SCSS compilation errors. Page background shows dark navy. Press Ctrl+C.

- [ ] **Step 6: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/styles/
git commit -m "feat(frontend): add dark theme styles based on TrafficMind"
```

---

## Task 3: Shared Types & API Client

**Files:**
- Create: `frontend/src/shared/types/index.ts`
- Create: `frontend/src/shared/api/types.ts`
- Create: `frontend/src/shared/api/client.ts`
- Create: `frontend/src/shared/api/modules/training.ts`
- Create: `frontend/src/shared/api/modules/conversion.ts`
- Create: `frontend/src/shared/api/modules/system.ts`

- [ ] **Step 1: Create shared types**

Create `frontend/src/shared/types/index.ts`:

```typescript
/** Pagination request params */
export interface PaginationParams {
  page: number
  page_size: number
  status?: string
}

/** Paginated response data wrapper */
export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** Generic API success envelope from backend */
export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
  request_id: string
  warnings: string[]
}

/** API error response */
export interface ApiErrorEnvelope {
  code: number
  message: string
  details: Record<string, unknown>
  request_id: string
}
```

- [ ] **Step 2: Create API types**

Create `frontend/src/shared/api/types.ts`:

```typescript
export type { ApiEnvelope, ApiErrorEnvelope, PaginationParams, PaginatedData } from '../types'
```

- [ ] **Step 3: Create API client**

Create `frontend/src/shared/api/client.ts`:

```typescript
import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiEnvelope, ApiErrorEnvelope } from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor
http.interceptors.request.use((config) => {
  return config
})

// Response interceptor — unwrap envelope
http.interceptors.response.use(
  (response) => {
    const body = response.data as ApiEnvelope<unknown>
    if (body.code !== 0) {
      const msg = body.message || '请求失败'
      ElMessage.error(msg)
      return Promise.reject(new Error(msg))
    }
    // Return the full envelope so callers can access warnings etc.
    return response
  },
  (error) => {
    if (error.response) {
      const body = error.response.data as ApiErrorEnvelope | undefined
      const msg = body?.message || `请求错误 (${error.response.status})`
      ElMessage.error(msg)
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络连接失败')
    }
    return Promise.reject(error)
  },
)

/** Typed GET — returns data field from envelope */
export async function apiGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const res = await http.get<ApiEnvelope<T>>(url, { params })
  return res.data.data
}

/** Typed POST — returns data field from envelope */
export async function apiPost<T>(url: string, data?: Record<string, unknown>): Promise<T> {
  const res = await http.post<ApiEnvelope<T>>(url, data)
  return res.data.data
}

/** POST that returns full envelope (for warnings access) */
export async function apiPostFull<T>(url: string, data?: Record<string, unknown>): Promise<ApiEnvelope<T>> {
  const res = await http.post<ApiEnvelope<T>>(url, data)
  return res.data
}

export { http }
```

- [ ] **Step 4: Create training API module**

Create `frontend/src/shared/api/modules/training.ts`:

```typescript
import { apiGet, apiPost, apiPostFull } from '../client'
import type { PaginationParams, PaginatedData } from '../types'

// ---------- Types ----------

export interface TrainingTaskSummary {
  id: number
  parent_task_id: number | null
  task_name: string
  task_group: string
  task_type: string
  task_source: string
  status: string
  clearml_task_id: string | null
  queue_name: string | null
  template_name: string | null
  params: Record<string, unknown>
  parameter_snapshot: Record<string, unknown>
  runtime_snapshot: Record<string, unknown>
  custom_data: Record<string, unknown>
  result_summary: Record<string, unknown>
  error_message: string | null
  last_sync_status: string | null
  last_sync_error: string | null
  sync_version: number
  created_at: string
  updated_at: string
}

export interface TrainingCreateMetaTemplate {
  name: string
  display_name: string | null
  queue: string | null
  entrypoint: string | null
  defaults: Record<string, unknown>
  runtime: {
    launcher: string
    script_path: string | null
    working_dir: string | null
    env: Record<string, string>
    artifacts: Array<{
      name: string
      role: string
      format: string
      path: string
    }>
  }
  execution_defaults: Record<string, unknown>
}

export interface TrainingCreateMetaQueue {
  queue_name: string
  agent_count: number
  has_online_agents: boolean
  agents: Array<{ name: string; status: string | null }>
  last_seen: string | null
}

export interface TrainingCreateMetaData {
  templates: TrainingCreateMetaTemplate[]
  queues: TrainingCreateMetaQueue[]
}

export interface TrainingCreateRequest {
  task_name: string
  template_name: string
  params: Record<string, unknown>
  execution_params?: Record<string, unknown>
  queue_name?: string | null
  custom_data?: Record<string, unknown>
}

export interface TrainingCreateSubmission {
  clearml_task_id: string | null
  status: string | null
}

export interface TrainingCreateResult {
  task: TrainingTaskSummary
  submission: TrainingCreateSubmission
}

// ---------- API Calls ----------

/** GET /training — paginated training task list */
export function getTrainingList(params: PaginationParams) {
  return apiGet<PaginatedData<TrainingTaskSummary>>('/training', params as Record<string, unknown>)
}

/** GET /training/:id — single training task detail */
export function getTrainingDetail(id: number) {
  return apiGet<TrainingTaskSummary>(`/training/${id}`)
}

/** GET /training/create-meta — templates + queues metadata */
export function getTrainingCreateMeta() {
  return apiGet<TrainingCreateMetaData>('/training/create-meta')
}

/** POST /training — create a new training task */
export function createTraining(data: TrainingCreateRequest) {
  return apiPostFull<TrainingCreateResult>('/training', data as Record<string, unknown>)
}
```

- [ ] **Step 5: Create conversion API module**

Create `frontend/src/shared/api/modules/conversion.ts`:

```typescript
import { apiPostFull } from '../client'
import type { TrainingCreateResult } from './training'

export interface ConversionCreateRequest {
  parent_task_id: number
  task_name?: string | null
  params?: Record<string, unknown>
  execution_params?: Record<string, unknown>
}

/** POST /conversion/onnx — create ONNX export task */
export function createOnnxConversion(data: ConversionCreateRequest) {
  return apiPostFull<TrainingCreateResult>('/conversion/onnx', data as Record<string, unknown>)
}
```

- [ ] **Step 6: Create system API module**

Create `frontend/src/shared/api/modules/system.ts`:

```typescript
import { apiGet } from '../client'

export interface HealthData {
  status: string
  app_name: string
}

export interface SchedulerStatus {
  enabled: boolean
  running: boolean
  job_count: number
}

export interface RuntimeData {
  scheduler: SchedulerStatus
}

/** GET /system/health */
export function getHealth() {
  return apiGet<HealthData>('/system/health')
}

/** GET /system/runtime */
export function getRuntime() {
  return apiGet<RuntimeData>('/system/runtime')
}
```

- [ ] **Step 7: Verify compilation**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm build
```

Expected: Build completes without type errors.

- [ ] **Step 8: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/shared/
git commit -m "feat(frontend): add shared types and API client layer"
```

---

## Task 4: Shared Utils & Composables

**Files:**
- Create: `frontend/src/shared/utils/format.ts`
- Create: `frontend/src/shared/utils/constants.ts`
- Create: `frontend/src/shared/composables/usePagination.ts`
- Create: `frontend/src/shared/composables/useLoading.ts`
- Create: `frontend/src/shared/stores/app.ts`

- [ ] **Step 1: Create format utils**

Create `frontend/src/shared/utils/format.ts`:

```typescript
/** Format ISO datetime to locale display string */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** Format bytes to human-readable size */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}
```

- [ ] **Step 2: Create constants**

Create `frontend/src/shared/utils/constants.ts`:

```typescript
/** Task status display name mapping */
export const TASK_STATUS_MAP: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

/** Task status to Element Plus tag type */
export const TASK_STATUS_TAG_TYPE: Record<string, string> = {
  queued: 'info',
  running: '',
  succeeded: 'success',
  failed: 'danger',
  cancelled: 'warning',
}

/** Task status to custom color override */
export const TASK_STATUS_COLOR: Record<string, string> = {
  queued: '#5f739c',
  running: '#3b82f6',
  succeeded: '#36e08a',
  failed: '#ff5a6e',
  cancelled: '#ffb020',
}
```

- [ ] **Step 3: Create usePagination composable**

Create `frontend/src/shared/composables/usePagination.ts`:

```typescript
import { reactive, computed } from 'vue'

export function usePagination(defaultPageSize = 20) {
  const state = reactive({
    page: 1,
    pageSize: defaultPageSize,
    total: 0,
  })

  const totalPages = computed(() => Math.ceil(state.total / state.pageSize) || 1)

  function onPageChange(page: number) {
    state.page = page
  }

  function onSizeChange(size: number) {
    state.pageSize = size
    state.page = 1
  }

  function reset() {
    state.page = 1
    state.total = 0
  }

  return {
    page: computed(() => state.page),
    pageSize: computed(() => state.pageSize),
    total: computed(() => state.total),
    totalPages,
    setTotal: (n: number) => { state.total = n },
    onPageChange,
    onSizeChange,
    reset,
  }
}
```

- [ ] **Step 4: Create useLoading composable**

Create `frontend/src/shared/composables/useLoading.ts`:

```typescript
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export function useLoading() {
  const loading = ref(false)

  async function withLoading<T>(fn: () => Promise<T>): Promise<T | undefined> {
    loading.value = true
    try {
      return await fn()
    } catch (e: unknown) {
      // Error already handled by API interceptor; re-surface if needed
      throw e
    } finally {
      loading.value = false
    }
  }

  async function withLoadingSafe<T>(fn: () => Promise<T>): Promise<T | undefined> {
    try {
      return await withLoading(fn)
    } catch {
      return undefined
    }
  }

  return { loading, withLoading, withLoadingSafe }
}
```

- [ ] **Step 5: Create app store**

Create `frontend/src/shared/stores/app.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { sidebarCollapsed, toggleSidebar }
})
```

- [ ] **Step 6: Verify compilation**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm build
```

Expected: Build passes.

- [ ] **Step 7: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/shared/
git commit -m "feat(frontend): add shared utils, composables, and app store"
```

---

## Task 5: Shared Components

**Files:**
- Create: `frontend/src/shared/components/PageHeader.vue`
- Create: `frontend/src/shared/components/JsonViewer.vue`
- Create: `frontend/src/shared/components/StatusTag.vue`
- Create: `frontend/src/shared/components/EmptyState.vue`
- Create: `frontend/src/shared/components/PlaceholderPage.vue`

- [ ] **Step 1: Create PageHeader.vue**

Create `frontend/src/shared/components/PageHeader.vue`:

```vue
<template>
  <div class="page-h">
    <h2>
      <span class="page-bar" />
      {{ title }}
    </h2>
    <p v-if="subtitle">{{ subtitle }}</p>
    <div class="page-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped>
.page-h {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  margin-bottom: 16px;
}
.page-h h2 {
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 1px;
}
.page-h p {
  color: var(--txt2);
  font-size: 12.5px;
  margin-bottom: 2px;
}
.page-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
</style>
```

- [ ] **Step 2: Create JsonViewer.vue**

Create `frontend/src/shared/components/JsonViewer.vue`:

```vue
<template>
  <div class="json-viewer">
    <pre><code>{{ formatted }}</code></pre>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: Record<string, unknown> | unknown[] | null | undefined
}>()

const formatted = computed(() => {
  if (!props.data) return '-'
  return JSON.stringify(props.data, null, 2)
})
</script>

<style scoped>
.json-viewer {
  background: #08152e;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}
.json-viewer pre {
  margin: 0;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--txt);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
```

- [ ] **Step 3: Create StatusTag.vue**

Create `frontend/src/shared/components/StatusTag.vue`:

```vue
<template>
  <el-tag :type="tagType" :color="customColor" :style="tagStyle" size="small" effect="dark">
    {{ label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TASK_STATUS_MAP, TASK_STATUS_TAG_TYPE, TASK_STATUS_COLOR } from '@/shared/utils/constants'

const props = defineProps<{
  status: string
}>()

const label = computed(() => TASK_STATUS_MAP[props.status] || props.status)
const tagType = computed(() => TASK_STATUS_TAG_TYPE[props.status] || 'info')
const customColor = computed(() => TASK_STATUS_COLOR[props.status] || '')

const tagStyle = computed(() => {
  if (!customColor.value) return {}
  return {
    backgroundColor: `${customColor.value}22`,
    color: customColor.value,
    borderColor: `${customColor.value}44`,
  }
})
</script>
```

- [ ] **Step 4: Create EmptyState.vue**

Create `frontend/src/shared/components/EmptyState.vue`:

```vue
<template>
  <div class="empty-state">
    <el-empty :description="description" :image-size="120" />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ description?: string }>(), {
  description: '暂无数据',
})
</script>

<style scoped>
.empty-state {
  padding: 40px 0;
  text-align: center;
}
</style>
```

- [ ] **Step 5: Create PlaceholderPage.vue**

Create `frontend/src/shared/components/PlaceholderPage.vue`:

```vue
<template>
  <div class="placeholder-page">
    <div class="placeholder-content">
      <h2>
        <span class="page-bar" />
        {{ title }}
      </h2>
      <p>该功能正在开发中，敬请期待。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
}>()
</script>

<style scoped>
.placeholder-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
.placeholder-content {
  text-align: center;
}
.placeholder-content h2 {
  font-size: 21px;
  font-weight: 700;
  margin-bottom: 12px;
}
.placeholder-content p {
  color: var(--muted);
  font-size: 14px;
}
</style>
```

- [ ] **Step 6: Verify compilation**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm build
```

Expected: Build passes.

- [ ] **Step 7: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/shared/components/
git commit -m "feat(frontend): add shared UI components"
```

---

## Task 6: App Layout & Router

**Files:**
- Create: `frontend/src/app/layouts/AppHeader.vue`
- Create: `frontend/src/app/layouts/AppSidebar.vue`
- Create: `frontend/src/app/layouts/MainLayout.vue`
- Create: `frontend/src/app/router/index.ts`
- Modify: `frontend/src/main.ts` — add router
- Modify: `frontend/src/App.vue` — use router-view

- [ ] **Step 1: Create AppHeader.vue**

Create `frontend/src/app/layouts/AppHeader.vue`:

```vue
<template>
  <header class="app-header">
    <div class="logo" @click="router.push('/')">
      <div class="mark">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
          <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" stroke="#dbeafe" stroke-width="1.5" stroke-linejoin="round" />
          <path d="M12 8l-4 2v4l4 2 4-2v-4l-4-2z" stroke="#28e0e0" stroke-width="1.5" stroke-linejoin="round" />
        </svg>
      </div>
      <h1>M<b>LOps</b></h1>
    </div>
    <div class="spacer" />
    <span class="clock font-mono">{{ clock }}</span>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const clock = ref('')
let timer: ReturnType<typeof setInterval> | null = null

function tick() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  clock.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

onMounted(() => {
  tick()
  timer = setInterval(tick, 1000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 22px;
  height: 60px;
  background: linear-gradient(180deg, rgba(18, 40, 80, 0.85), rgba(10, 22, 48, 0.6));
  border-bottom: 1px solid var(--line2);
  backdrop-filter: blur(6px);
}
.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}
.mark {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: linear-gradient(145deg, #08162f, #102b57, #071226);
  border: 1px solid rgba(109, 197, 255, 0.32);
  box-shadow: var(--glow);
}
.logo h1 {
  font-size: 19px;
  letter-spacing: 1.4px;
  font-weight: 700;
  color: var(--txt);
}
.logo h1 b {
  color: var(--cyan);
}
.spacer {
  flex: 1;
}
.clock {
  font-size: 13px;
  color: var(--txt2);
  border-left: 1px solid var(--line);
  padding-left: 18px;
}
</style>
```

- [ ] **Step 2: Create AppSidebar.vue**

Create `frontend/src/app/layouts/AppSidebar.vue`:

```vue
<template>
  <nav class="app-sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div
      v-for="item in navItems"
      :key="item.path"
      class="nav-item"
      :class="{ active: isActive(item.path) }"
      @click="router.push(item.path)"
    >
      <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
      <span v-if="!appStore.sidebarCollapsed" class="nav-label">{{ item.label }}</span>
    </div>

    <div class="nav-divider" />

    <div
      v-for="item in placeholderItems"
      :key="item.path"
      class="nav-item"
      :class="{ active: isActive(item.path) }"
      @click="router.push(item.path)"
    >
      <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
      <span v-if="!appStore.sidebarCollapsed" class="nav-label">{{ item.label }}</span>
      <span v-if="!appStore.sidebarCollapsed" class="nav-tag">规划中</span>
    </div>

    <div class="nav-bottom">
      <div class="nav-item" @click="appStore.toggleSidebar()">
        <el-icon class="nav-icon">
          <Fold v-if="!appStore.sidebarCollapsed" />
          <Expand v-else />
        </el-icon>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { Aim, Document, Box, User, Fold, Expand } from '@element-plus/icons-vue'
import { useAppStore } from '@/shared/stores/app'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const navItems = [
  { path: '/training', label: '训练任务', icon: Aim },
  { path: '/template', label: '模板管理', icon: Document },
]

const placeholderItems = [
  { path: '/model-registry', label: '模型仓库', icon: Box },
  { path: '/auth', label: '用户管理', icon: User },
]

function isActive(path: string): boolean {
  return route.path.startsWith(path)
}
</script>

<style scoped>
.app-sidebar {
  padding: 14px 12px;
  border-right: 1px solid var(--line);
  overflow-y: auto;
  background: linear-gradient(180deg, rgba(14, 29, 61, 0.5), transparent);
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  width: 220px;
}
.app-sidebar.collapsed {
  width: 56px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 13px;
  border-radius: 10px;
  cursor: pointer;
  color: var(--txt2);
  font-size: 13.5px;
  margin-bottom: 3px;
  border: 1px solid transparent;
  transition: 0.18s;
  position: relative;
}
.nav-item:hover {
  background: var(--panel);
  color: var(--txt);
}
.nav-item.active {
  background: linear-gradient(90deg, rgba(40, 224, 224, 0.16), rgba(59, 130, 246, 0.06));
  color: #fff;
  border-color: var(--line2);
}
.nav-item.active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 3px;
  background: var(--cyan);
  box-shadow: var(--glow);
}
.nav-icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}
.nav-label {
  white-space: nowrap;
}
.nav-tag {
  margin-left: auto;
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.2);
  color: var(--teal);
}
.nav-divider {
  height: 1px;
  background: var(--line);
  margin: 12px 0;
}
.nav-bottom {
  margin-top: auto;
}
</style>
```

- [ ] **Step 3: Create MainLayout.vue**

Create `frontend/src/app/layouts/MainLayout.vue`:

```vue
<template>
  <div class="main-layout">
    <AppHeader />
    <div class="main-body">
      <AppSidebar />
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
</script>

<style scoped>
.main-layout {
  display: grid;
  grid-template-rows: 60px 1fr;
  height: 100vh;
}
.main-body {
  display: flex;
  overflow: hidden;
}
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 40px;
}
</style>
```

- [ ] **Step 4: Create router**

Create `frontend/src/app/router/index.ts`:

```typescript
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/training',
    children: [
      // Training module routes (lazy-loaded)
      {
        path: 'training',
        name: 'TrainingList',
        component: () => import('@/modules/training/components/TaskListPage.vue'),
      },
      {
        path: 'training/:id',
        name: 'TrainingDetail',
        component: () => import('@/modules/training/components/TaskDetailPage.vue'),
        props: true,
      },
      // Template module routes
      {
        path: 'template',
        name: 'TemplateList',
        component: () => import('@/modules/template/components/TemplateListPage.vue'),
      },
      // Placeholder modules
      {
        path: 'model-registry',
        name: 'ModelRegistry',
        component: () => import('@/modules/model-registry/components/PlaceholderPage.vue'),
        props: { title: '模型仓库' },
      },
      {
        path: 'auth',
        name: 'Auth',
        component: () => import('@/modules/auth/components/PlaceholderPage.vue'),
        props: { title: '用户管理' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

- [ ] **Step 5: Update main.ts**

Replace `frontend/src/main.ts`:

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/theme-chalk/src/index.scss'
import '@/styles/global.scss'
import '@/styles/dark-overrides.scss'
import '@/styles/theme.css'
import router from './app/router'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 6: Update App.vue**

Replace `frontend/src/App.vue`:

```vue
<template>
  <router-view />
</template>
```

- [ ] **Step 7: Create placeholder module files for routing**

Create the minimum placeholder files needed by the router:

Create `frontend/src/modules/model-registry/components/PlaceholderPage.vue`:
```vue
<template>
  <PlaceholderPage :title="title" />
</template>

<script setup lang="ts">
import PlaceholderPage from '@/shared/components/PlaceholderPage.vue'

defineProps<{ title: string }>()
</script>
```

Create `frontend/src/modules/auth/components/PlaceholderPage.vue`:
```vue
<template>
  <PlaceholderPage :title="title" />
</template>

<script setup lang="ts">
import PlaceholderPage from '@/shared/components/PlaceholderPage.vue'

defineProps<{ title: string }>()
</script>
```

- [ ] **Step 8: Verify dev server renders layout**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm dev
```

Expected: Dev server starts. Open http://localhost:3000 — should show dark header with MLOps logo, sidebar with navigation items. Clicking "模型仓库" or "用户管理" shows placeholder page. Press Ctrl+C.

- [ ] **Step 9: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/
git commit -m "feat(frontend): add app layout, router, and sidebar navigation"
```

---

## Task 7: Training Module — Types, Store, Composable

**Files:**
- Create: `frontend/src/modules/training/types/index.ts`
- Create: `frontend/src/modules/training/stores/training.ts`
- Create: `frontend/src/modules/training/composables/useTrainingList.ts`
- Create: `frontend/src/modules/training/routes.ts`
- Create: `frontend/src/modules/training/index.ts`

- [ ] **Step 1: Create training types**

Create `frontend/src/modules/training/types/index.ts`:

```typescript
// Re-export API types for module-internal use
export type {
  TrainingTaskSummary,
  TrainingCreateMetaTemplate,
  TrainingCreateMetaQueue,
  TrainingCreateMetaData,
  TrainingCreateRequest,
  TrainingCreateResult,
} from '@/shared/api/modules/training'
```

- [ ] **Step 2: Create training store**

Create `frontend/src/modules/training/stores/training.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TrainingTaskSummary, TrainingCreateMetaData } from '@/shared/api/modules/training'
import { getTrainingCreateMeta } from '@/shared/api/modules/training'

export const useTrainingStore = defineStore('training', () => {
  const createMeta = ref<TrainingCreateMetaData | null>(null)
  const createMetaLoading = ref(false)

  async function loadCreateMeta() {
    createMetaLoading.value = true
    try {
      createMeta.value = await getTrainingCreateMeta()
    } finally {
      createMetaLoading.value = false
    }
  }

  return { createMeta, createMetaLoading, loadCreateMeta }
})
```

- [ ] **Step 3: Create useTrainingList composable**

Create `frontend/src/modules/training/composables/useTrainingList.ts`:

```typescript
import { ref, watch } from 'vue'
import { getTrainingList } from '@/shared/api/modules/training'
import type { TrainingTaskSummary } from '@/shared/api/modules/training'
import { usePagination } from '@/shared/composables/usePagination'
import { useLoading } from '@/shared/composables/useLoading'

export function useTrainingList() {
  const { page, pageSize, total, setTotal, onPageChange, onSizeChange, reset } = usePagination(20)
  const { loading, withLoadingSafe } = useLoading()

  const items = ref<TrainingTaskSummary[]>([])
  const statusFilter = ref('')

  async function fetchList() {
    await withLoadingSafe(async () => {
      const params: Record<string, unknown> = {
        page: page.value,
        page_size: pageSize.value,
      }
      if (statusFilter.value) {
        params.status = statusFilter.value
      }
      const data = await getTrainingList(params as any)
      items.value = data.items
      setTotal(data.total)
    })
  }

  // Re-fetch when page/size/filter changes
  watch([page, pageSize, statusFilter], () => { fetchList() })

  return {
    items,
    loading,
    page,
    pageSize,
    total,
    statusFilter,
    onPageChange,
    onSizeChange,
    fetchList,
    reset,
  }
}
```

- [ ] **Step 4: Create module route file**

Create `frontend/src/modules/training/routes.ts`:

```typescript
import type { RouteRecordRaw } from 'vue-router'

export const trainingRoutes: RouteRecordRaw[] = [
  {
    path: 'training',
    name: 'TrainingList',
    component: () => import('./components/TaskListPage.vue'),
  },
  {
    path: 'training/:id',
    name: 'TrainingDetail',
    component: () => import('./components/TaskDetailPage.vue'),
    props: true,
  },
]
```

- [ ] **Step 5: Create module index**

Create `frontend/src/modules/training/index.ts`:

```typescript
export { useTrainingStore } from './stores/training'
export { useTrainingList } from './composables/useTrainingList'
```

- [ ] **Step 6: Verify compilation**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm build
```

Expected: Build passes.

- [ ] **Step 7: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/modules/training/
git commit -m "feat(frontend): add training module types, store, and composable"
```

---

## Task 8: Training Module — TaskListPage

**Files:**
- Create: `frontend/src/modules/training/components/TaskStatusTag.vue`
- Create: `frontend/src/modules/training/components/TaskListPage.vue`

- [ ] **Step 1: Create TaskStatusTag.vue**

Create `frontend/src/modules/training/components/TaskStatusTag.vue`:

```vue
<template>
  <el-tag
    :type="tagType"
    size="small"
    effect="dark"
    :style="tagStyle"
  >
    {{ label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TASK_STATUS_MAP, TASK_STATUS_TAG_TYPE, TASK_STATUS_COLOR } from '@/shared/utils/constants'

const props = defineProps<{ status: string }>()

const label = computed(() => TASK_STATUS_MAP[props.status] || props.status)
const tagType = computed(() => TASK_STATUS_TAG_TYPE[props.status] || 'info')

const tagStyle = computed(() => {
  const color = TASK_STATUS_COLOR[props.status]
  if (!color) return {}
  return {
    backgroundColor: `${color}22`,
    color,
    borderColor: `${color}44`,
  }
})
</script>
```

- [ ] **Step 2: Create TaskListPage.vue**

Create `frontend/src/modules/training/components/TaskListPage.vue`:

```vue
<template>
  <div class="task-list-page">
    <PageHeader title="训练任务">
      <template #actions>
        <el-select
          v-model="statusFilter"
          placeholder="状态筛选"
          clearable
          style="width: 140px"
        >
          <el-option label="排队中" value="queued" />
          <el-option label="运行中" value="running" />
          <el-option label="已完成" value="succeeded" />
          <el-option label="失败" value="failed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-button type="primary" @click="showCreateDrawer = true">
          创建训练任务
        </el-button>
      </template>
    </PageHeader>

    <el-table
      :data="items"
      v-loading="loading"
      stripe
      @row-click="handleRowClick"
      style="cursor: pointer"
    >
      <el-table-column prop="task_name" label="任务名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="template_name" label="模板" width="140" show-overflow-tooltip />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <TaskStatusTag :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column prop="queue_name" label="队列" width="140" show-overflow-tooltip />
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">
          <span class="font-mono">{{ formatTime(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="goDetail(row.id)">
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>

    <CreateTaskDrawer v-model="showCreateDrawer" @created="fetchList" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/shared/components/PageHeader.vue'
import TaskStatusTag from './TaskStatusTag.vue'
import CreateTaskDrawer from './CreateTaskDrawer.vue'
import { useTrainingList } from '../composables/useTrainingList'
import { formatTime } from '@/shared/utils/format'

const router = useRouter()
const { items, loading, page, pageSize, total, statusFilter, onPageChange, onSizeChange, fetchList } = useTrainingList()

const showCreateDrawer = ref(false)

function handleRowClick(row: { id: number }) {
  router.push(`/training/${row.id}`)
}

function goDetail(id: number) {
  router.push(`/training/${id}`)
}

onMounted(() => { fetchList() })
</script>

<style scoped>
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
```

- [ ] **Step 3: Create a temporary stub for CreateTaskDrawer**

Since CreateTaskDrawer hasn't been built yet, create a minimal stub so TaskListPage compiles:

Create `frontend/src/modules/training/components/CreateTaskDrawer.vue`:

```vue
<template>
  <div><!-- stub: will be implemented in Task 9 --></div>
</template>

<script setup lang="ts">
defineEmits<{
  (e: 'created'): void
}>()

defineModel<boolean>({ required: true })
</script>
```

- [ ] **Step 4: Verify page renders**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm dev
```

Expected: Navigate to http://localhost:3000 — sidebar shows, training list page renders with empty table (no backend connection needed to verify UI). Press Ctrl+C.

- [ ] **Step 5: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/modules/training/components/
git commit -m "feat(frontend): add training task list page with table and pagination"
```

---

## Task 9: Training Module — CreateTaskDrawer

**Files:**
- Modify: `frontend/src/modules/training/components/CreateTaskDrawer.vue` — replace stub with full implementation

- [ ] **Step 1: Implement CreateTaskDrawer.vue**

Replace `frontend/src/modules/training/components/CreateTaskDrawer.vue`:

```vue
<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="创建训练任务"
    direction="rtl"
    size="480px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="任务名称" prop="task_name">
        <el-input v-model="form.task_name" placeholder="输入任务名称" />
      </el-form-item>

      <el-form-item label="选择模板" prop="template_name">
        <el-select
          v-model="form.template_name"
          placeholder="请选择模板"
          style="width: 100%"
          @change="handleTemplateChange"
        >
          <el-option
            v-for="t in templates"
            :key="t.name"
            :label="t.display_name || t.name"
            :value="t.name"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="选择队列">
        <el-select
          v-model="form.queue_name"
          placeholder="请选择队列"
          style="width: 100%"
          clearable
        >
          <el-option
            v-for="q in queues"
            :key="q.queue_name"
            :label="`${q.queue_name} (${q.agent_count} agents)`"
            :value="q.queue_name"
          >
            <span>{{ q.queue_name }}</span>
            <span style="float: right; color: var(--muted); font-size: 12px">
              {{ q.agent_count }} agents
              <span v-if="!q.has_online_agents" style="color: var(--amber)"> (离线)</span>
            </span>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item v-if="selectedTemplate" label="模板参数">
        <div class="param-editor">
          <div v-for="(value, key) in form.params" :key="key" class="param-row">
            <span class="param-key">{{ key }}</span>
            <el-input
              :model-value="String(value)"
              @update:model-value="updateParam(key, $event)"
              size="small"
            />
          </div>
          <div v-if="Object.keys(form.params).length === 0" class="text-muted" style="font-size: 12px">
            该模板无默认参数
          </div>
        </div>
      </el-form-item>

      <div class="drawer-footer">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          提交任务
        </el-button>
      </div>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useTrainingStore } from '../stores/training'
import { createTraining } from '@/shared/api/modules/training'

const modelValue = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (e: 'created'): void }>()

const trainingStore = useTrainingStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const templates = computed(() => trainingStore.createMeta?.templates || [])
const queues = computed(() => trainingStore.createMeta?.queues || [])

const selectedTemplate = computed(() =>
  templates.value.find(t => t.name === form.value.template_name)
)

const form = ref({
  task_name: '',
  template_name: '',
  queue_name: null as string | null,
  params: {} as Record<string, unknown>,
})

const rules: FormRules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  template_name: [{ required: true, message: '请选择模板', trigger: 'change' }],
}

// Load create metadata when drawer opens
watch(modelValue, (val) => {
  if (val) {
    trainingStore.loadCreateMeta()
    form.value = { task_name: '', template_name: '', queue_name: null, params: {} }
  }
})

function handleTemplateChange(name: string) {
  const tpl = templates.value.find(t => t.name === name)
  form.value.queue_name = tpl?.queue || null
  form.value.params = tpl ? { ...tpl.defaults } : {}
}

function updateParam(key: string, val: string) {
  form.value.params[key] = val
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const result = await createTraining({
      task_name: form.value.task_name,
      template_name: form.value.template_name,
      params: form.value.params,
      queue_name: form.value.queue_name,
    })

    // Show warnings if any
    if (result.warnings?.length) {
      result.warnings.forEach(w => ElMessage.warning(w))
    }

    ElMessage.success('训练任务已创建')
    modelValue.value = false
    emit('created')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.param-editor {
  width: 100%;
}
.param-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.param-key {
  min-width: 120px;
  font-size: 12.5px;
  color: var(--txt2);
  font-family: Consolas, monospace;
}
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
</style>
```

- [ ] **Step 2: Verify drawer compiles**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm build
```

Expected: Build passes.

- [ ] **Step 3: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/modules/training/components/CreateTaskDrawer.vue
git commit -m "feat(frontend): add create training task drawer with dynamic params"
```

---

## Task 10: Training Module — TaskDetailPage & ConversionDrawer

**Files:**
- Create: `frontend/src/modules/training/components/ConversionDrawer.vue`
- Create: `frontend/src/modules/training/components/TaskDetailPage.vue`

- [ ] **Step 1: Create ConversionDrawer.vue**

Create `frontend/src/modules/training/components/ConversionDrawer.vue`:

```vue
<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="导出为 ONNX"
    direction="rtl"
    size="440px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="源任务">
        <el-input :model-value="taskName" disabled />
      </el-form-item>

      <el-form-item label="任务名称">
        <el-input v-model="form.task_name" placeholder="导出任务名称" />
      </el-form-item>

      <el-form-item label="转换参数 (JSON)">
        <el-input
          v-model="paramsJson"
          type="textarea"
          :rows="6"
          placeholder='{"opset_version": 12, "simplify": true}'
        />
      </el-form-item>

      <div class="drawer-footer">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          发起导出
        </el-button>
      </div>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { createOnnxConversion } from '@/shared/api/modules/conversion'

const props = defineProps<{
  taskId: number
  taskName: string
}>()

const modelValue = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (e: 'submitted'): void }>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = ref({
  task_name: '',
})

const paramsJson = ref('{\n  "opset_version": 12,\n  "simplify": true\n}')

// Auto-fill name when opened
watch(modelValue, (val) => {
  if (val) {
    form.value.task_name = `${props.taskName}-onnx`
  }
})

async function handleSubmit() {
  let params: Record<string, unknown> = {}
  try {
    params = JSON.parse(paramsJson.value || '{}')
  } catch {
    ElMessage.error('参数 JSON 格式错误')
    return
  }

  submitting.value = true
  try {
    const result = await createOnnxConversion({
      parent_task_id: props.taskId,
      task_name: form.value.task_name || undefined,
      params,
    })

    if (result.warnings?.length) {
      result.warnings.forEach(w => ElMessage.warning(w))
    }

    ElMessage.success('ONNX 导出任务已创建')
    modelValue.value = false
    emit('submitted')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
</style>
```

- [ ] **Step 2: Create TaskDetailPage.vue**

Create `frontend/src/modules/training/components/TaskDetailPage.vue`:

```vue
<template>
  <div class="task-detail-page">
    <div class="detail-header">
      <el-button link @click="router.push('/training')">
        ← 返回列表
      </el-button>
      <h2 style="margin-left: 12px">{{ task?.task_name || '加载中...' }}</h2>
    </div>

    <div v-if="loading" style="padding: 40px; text-align: center">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <template v-else-if="task">
      <!-- Basic Info -->
      <el-card class="detail-card">
        <template #header>
          <span class="card-dot" />基本信息
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务名称">{{ task.task_name }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">{{ task.task_type }}</el-descriptions-item>
          <el-descriptions-item label="模板">{{ task.template_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <TaskStatusTag :status="task.status" />
          </el-descriptions-item>
          <el-descriptions-item label="队列">{{ task.queue_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ task.task_source }}</el-descriptions-item>
          <el-descriptions-item label="ClearML ID">
            <span class="font-mono">{{ task.clearml_task_id || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            <span class="font-mono">{{ formatTime(task.created_at) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            <span class="font-mono">{{ formatTime(task.updated_at) }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="task.error_message" label="错误信息">
            <span style="color: var(--red)">{{ task.error_message }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- Parameter Snapshot -->
      <el-card v-if="task.parameter_snapshot && Object.keys(task.parameter_snapshot).length" class="detail-card">
        <template #header>
          <span class="card-dot" />参数快照
        </template>
        <JsonViewer :data="task.parameter_snapshot" />
      </el-card>

      <!-- Runtime Snapshot -->
      <el-card v-if="task.runtime_snapshot && Object.keys(task.runtime_snapshot).length" class="detail-card">
        <template #header>
          <span class="card-dot" />运行时信息
        </template>
        <JsonViewer :data="task.runtime_snapshot" />
      </el-card>

      <!-- Result Summary -->
      <el-card v-if="task.result_summary && Object.keys(task.result_summary).length" class="detail-card">
        <template #header>
          <span class="card-dot" />结果摘要
        </template>
        <JsonViewer :data="task.result_summary" />
      </el-card>

      <!-- Actions -->
      <el-card class="detail-card">
        <template #header>
          <span class="card-dot" />操作
        </template>
        <div class="actions">
          <el-button
            type="primary"
            :disabled="task.status !== 'succeeded'"
            @click="showConversionDrawer = true"
          >
            🔄 导出为 ONNX
          </el-button>
          <el-button disabled title="等后端 API 就绪后激活">
            📦 注册到模型仓库
          </el-button>
        </div>
      </el-card>

      <ConversionDrawer
        v-model="showConversionDrawer"
        :task-id="task.id"
        :task-name="task.task_name"
        @submitted="loadTask"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import TaskStatusTag from './TaskStatusTag.vue'
import ConversionDrawer from './ConversionDrawer.vue'
import JsonViewer from '@/shared/components/JsonViewer.vue'
import { getTrainingDetail, type TrainingTaskSummary } from '@/shared/api/modules/training'
import { formatTime } from '@/shared/utils/format'

const props = defineProps<{ id: string }>()
const router = useRouter()

const task = ref<TrainingTaskSummary | null>(null)
const loading = ref(true)
const showConversionDrawer = ref(false)

async function loadTask() {
  loading.value = true
  try {
    task.value = await getTrainingDetail(Number(props.id))
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadTask() })
</script>

<style scoped>
.detail-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}
.detail-header h2 {
  font-size: 20px;
  font-weight: 700;
}
.detail-card {
  margin-bottom: 16px;
}
.actions {
  display: flex;
  gap: 10px;
}
</style>
```

- [ ] **Step 3: Verify build**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm build
```

Expected: Build passes.

- [ ] **Step 4: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/modules/training/components/
git commit -m "feat(frontend): add task detail page and ONNX conversion drawer"
```

---

## Task 11: Template Module

**Files:**
- Create: `frontend/src/modules/template/types/index.ts`
- Create: `frontend/src/modules/template/stores/template.ts`
- Create: `frontend/src/modules/template/composables/useTemplates.ts`
- Create: `frontend/src/modules/template/routes.ts`
- Create: `frontend/src/modules/template/index.ts`
- Create: `frontend/src/modules/template/components/TemplateCard.vue`
- Create: `frontend/src/modules/template/components/TemplateDetailDialog.vue`
- Create: `frontend/src/modules/template/components/TemplateListPage.vue`

- [ ] **Step 1: Create template types**

Create `frontend/src/modules/template/types/index.ts`:

```typescript
export type {
  TrainingCreateMetaTemplate as TemplateItem,
  TrainingCreateMetaQueue as QueueStatusItem,
  TrainingCreateMetaData as TemplateListData,
} from '@/shared/api/modules/training'
```

- [ ] **Step 2: Create template store**

Create `frontend/src/modules/template/stores/template.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TrainingCreateMetaData } from '@/shared/api/modules/training'
import { getTrainingCreateMeta } from '@/shared/api/modules/training'

export const useTemplateStore = defineStore('template', () => {
  const data = ref<TrainingCreateMetaData | null>(null)
  const loading = ref(false)

  async function loadTemplates() {
    if (data.value) return // cache
    loading.value = true
    try {
      data.value = await getTrainingCreateMeta()
    } finally {
      loading.value = false
    }
  }

  return { data, loading, loadTemplates }
})
```

- [ ] **Step 3: Create template composable**

Create `frontend/src/modules/template/composables/useTemplates.ts`:

```typescript
import { computed } from 'vue'
import { useTemplateStore } from '../stores/template'

export function useTemplates() {
  const store = useTemplateStore()

  const templates = computed(() => store.data?.templates || [])
  const loading = computed(() => store.loading)

  function load() {
    store.loadTemplates()
  }

  return { templates, loading, load }
}
```

- [ ] **Step 4: Create module route and index files**

Create `frontend/src/modules/template/routes.ts`:

```typescript
import type { RouteRecordRaw } from 'vue-router'

export const templateRoutes: RouteRecordRaw[] = [
  {
    path: 'template',
    name: 'TemplateList',
    component: () => import('./components/TemplateListPage.vue'),
  },
]
```

Create `frontend/src/modules/template/index.ts`:

```typescript
export { useTemplateStore } from './stores/template'
export { useTemplates } from './composables/useTemplates'
```

- [ ] **Step 5: Create TemplateCard.vue**

Create `frontend/src/modules/template/components/TemplateCard.vue`:

```vue
<template>
  <div class="template-card glow-card" @click="$emit('click')">
    <div class="card-header">
      <span class="card-dot" />
      <span class="card-title">{{ template.display_name || template.name }}</span>
    </div>
    <div class="card-body">
      <div class="card-row">
        <span class="label">模板编码</span>
        <span class="value font-mono">{{ template.name }}</span>
      </div>
      <div v-if="template.entrypoint" class="card-row">
        <span class="label">入口脚本</span>
        <span class="value font-mono">{{ template.entrypoint }}</span>
      </div>
      <div v-if="template.queue" class="card-row">
        <span class="label">默认队列</span>
        <span class="value">{{ template.queue }}</span>
      </div>
      <div class="card-row">
        <span class="label">默认参数</span>
        <span class="value">{{ paramCount }} 项</span>
      </div>
    </div>
    <div class="card-footer">
      <el-button link type="primary" size="small">查看详情</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TrainingCreateMetaTemplate } from '@/shared/api/modules/training'

const props = defineProps<{ template: TrainingCreateMetaTemplate }>()
defineEmits<{ (e: 'click'): void }>()

const paramCount = computed(() => Object.keys(props.template.defaults || {}).length)
</script>

<style scoped>
.template-card {
  background: linear-gradient(180deg, var(--panel), rgba(10, 22, 48, 0.6));
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
  cursor: pointer;
}
.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.card-title {
  font-size: 14px;
  font-weight: 700;
  color: #eaf1ff;
}
.card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.card-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}
.card-row .label {
  color: var(--muted);
}
.card-row .value {
  color: var(--txt2);
}
.card-footer {
  margin-top: 12px;
  text-align: right;
}
</style>
```

- [ ] **Step 6: Create TemplateDetailDialog.vue**

Create `frontend/src/modules/template/components/TemplateDetailDialog.vue`:

```vue
<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="`模板详情: ${template?.display_name || template?.name || ''}`"
    width="680px"
    destroy-on-close
  >
    <template v-if="template">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="模板名称">{{ template.name }}</el-descriptions-item>
        <el-descriptions-item label="显示名称">{{ template.display_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="默认队列">{{ template.queue || '-' }}</el-descriptions-item>
        <el-descriptions-item label="入口脚本">{{ template.entrypoint || '-' }}</el-descriptions-item>
      </el-descriptions>

      <h4 v-if="template.runtime" style="margin: 16px 0 8px; color: var(--txt)">运行时配置</h4>
      <el-descriptions v-if="template.runtime" :column="2" border>
        <el-descriptions-item label="启动器">{{ template.runtime.launcher }}</el-descriptions-item>
        <el-descriptions-item label="工作目录">{{ template.runtime.working_dir || '-' }}</el-descriptions-item>
        <el-descriptions-item label="脚本路径" :span="2">{{ template.runtime.script_path || '-' }}</el-descriptions-item>
      </el-descriptions>

      <h4 v-if="template.runtime?.artifacts?.length" style="margin: 16px 0 8px; color: var(--txt)">产物配置</h4>
      <el-table v-if="template.runtime?.artifacts?.length" :data="template.runtime.artifacts" size="small" stripe>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="role" label="角色" />
        <el-table-column prop="format" label="格式" />
        <el-table-column prop="path" label="路径" show-overflow-tooltip />
      </el-table>

      <h4 style="margin: 16px 0 8px; color: var(--txt)">默认参数</h4>
      <JsonViewer :data="template.defaults" />
    </template>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
      <el-button type="primary" @click="handleUseTemplate">
        使用此模板创建任务
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import JsonViewer from '@/shared/components/JsonViewer.vue'
import type { TrainingCreateMetaTemplate } from '@/shared/api/modules/training'

const props = defineProps<{
  template: TrainingCreateMetaTemplate | null
}>()

const modelValue = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (e: 'use-template', name: string): void }>()

const router = useRouter()

function handleUseTemplate() {
  if (props.template) {
    emit('update:modelValue', false)
    // Navigate to training page and open create drawer
    router.push({ path: '/training', query: { template: props.template.name } })
  }
}
</script>
```

- [ ] **Step 7: Create TemplateListPage.vue**

Create `frontend/src/modules/template/components/TemplateListPage.vue`:

```vue
<template>
  <div class="template-list-page">
    <PageHeader title="模板管理" subtitle="浏览可用的训练模板配置" />

    <div v-loading="loading" class="template-grid">
      <template v-if="templates.length">
        <TemplateCard
          v-for="tpl in templates"
          :key="tpl.name"
          :template="tpl"
          @click="openDetail(tpl)"
        />
      </template>
      <EmptyState v-else description="暂无可用模板" />
    </div>

    <TemplateDetailDialog
      v-model="showDetail"
      :template="selectedTemplate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import EmptyState from '@/shared/components/EmptyState.vue'
import TemplateCard from './TemplateCard.vue'
import TemplateDetailDialog from './TemplateDetailDialog.vue'
import { useTemplates } from '../composables/useTemplates'
import type { TrainingCreateMetaTemplate } from '@/shared/api/modules/training'

const { templates, loading, load } = useTemplates()
const showDetail = ref(false)
const selectedTemplate = ref<TrainingCreateMetaTemplate | null>(null)

function openDetail(tpl: TrainingCreateMetaTemplate) {
  selectedTemplate.value = tpl
  showDetail.value = true
}

onMounted(() => { load() })
</script>

<style scoped>
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
</style>
```

- [ ] **Step 8: Verify build**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm build
```

Expected: Build passes.

- [ ] **Step 9: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/modules/template/
git commit -m "feat(frontend): add template management module with card grid and detail dialog"
```

---

## Task 12: Placeholder Modules — model-registry & auth

**Files:**
- Create: `frontend/src/modules/model-registry/types/index.ts`
- Create: `frontend/src/modules/model-registry/routes.ts`
- Create: `frontend/src/modules/model-registry/index.ts`
- Create: `frontend/src/modules/auth/types/index.ts`
- Create: `frontend/src/modules/auth/routes.ts`
- Create: `frontend/src/modules/auth/index.ts`

- [ ] **Step 1: Create model-registry module skeleton**

Create `frontend/src/modules/model-registry/types/index.ts`:

```typescript
/** Model Family — for future model registry module */
export interface ModelFamily {
  id: number
  code: string
  name: string
  model_type: string | null
  description: string | null
  status: string
  created_at: string
  updated_at: string
}

/** Model Version */
export interface ModelVersion {
  id: number
  model_family_id: number
  version: string
  version_name: string | null
  status: string
  source_task_id: number | null
  description: string | null
  registered_at: string | null
  created_at: string
  updated_at: string
}

/** Model File */
export interface ModelFile {
  id: number
  model_version_id: number | null
  source_task_id: number | null
  parent_model_file_id: number | null
  file_name: string
  file_type: string
  storage_uri: string | null
  framework: string | null
  status: string
  created_at: string
  updated_at: string
}
```

Create `frontend/src/modules/model-registry/routes.ts`:

```typescript
import type { RouteRecordRaw } from 'vue-router'

export const modelRegistryRoutes: RouteRecordRaw[] = [
  {
    path: 'model-registry',
    name: 'ModelRegistry',
    component: () => import('./components/PlaceholderPage.vue'),
    props: { title: '模型仓库' },
  },
]
```

Create `frontend/src/modules/model-registry/index.ts`:

```typescript
// Model Registry module — placeholder for future implementation
// Will be activated when backend model_registry API is ready
```

- [ ] **Step 2: Create auth module skeleton**

Create `frontend/src/modules/auth/types/index.ts`:

```typescript
/** User — for future IAM module */
export interface User {
  id: number
  username: string
  display_name: string | null
  email: string | null
  status: string
  created_at: string
  updated_at: string
}

/** Role */
export interface Role {
  id: number
  code: string
  name: string
  description: string | null
}

/** Permission */
export interface Permission {
  id: number
  code: string
  name: string
  module: string
}
```

Create `frontend/src/modules/auth/routes.ts`:

```typescript
import type { RouteRecordRaw } from 'vue-router'

export const authRoutes: RouteRecordRaw[] = [
  {
    path: 'auth',
    name: 'Auth',
    component: () => import('./components/PlaceholderPage.vue'),
    props: { title: '用户管理' },
  },
]
```

Create `frontend/src/modules/auth/index.ts`:

```typescript
// Auth module — placeholder for future IAM implementation
// Will be activated when backend IAM is ready
```

- [ ] **Step 3: Commit**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/src/modules/model-registry/ frontend/src/modules/auth/
git commit -m "feat(frontend): add placeholder modules for model-registry and auth"
```

---

## Task 13: Smoke Test & Final Verification

- [ ] **Step 1: Full build**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm build
```

Expected: Build passes with no errors.

- [ ] **Step 2: Start dev server and verify routes**

```bash
cd /mnt/d/workspace-2026/MLOps/frontend
pnpm dev
```

Open http://localhost:3000 and verify:

1. **/** redirects to `/training` — training list page shows header, sidebar, empty table
2. **/template** — template list page shows "暂无可用模板" (no backend connection)
3. **/model-registry** — shows "功能开发中" placeholder
4. **/auth** — shows "功能开发中" placeholder
5. Sidebar navigation works between all pages
6. Dark theme renders correctly (navy background, cyan accents)
7. Clock updates in header
8. Sidebar collapses with fold button

- [ ] **Step 3: Verify create drawer opens**

On the training list page, click "创建训练任务" — the drawer opens (will show empty template/queue selects since no backend is running, but no JS errors).

- [ ] **Step 4: Commit any final fixes**

```bash
cd /mnt/d/workspace-2026/MLOps
git add frontend/
git commit -m "chore(frontend): final verification and cleanup"
```
