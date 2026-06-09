# MLOps 前端设计文档

> 日期: 2026-06-08
> 状态: 已确认

---

## 1. 项目概述

为 MLOps 后端系统建设配套前端项目，采用模块化单体 SPA 架构，深色科技风 UI。

### 1.1 项目定位

- 内部运维工具 + 未来对外展示，UI 需有品质感
- 前后端分离部署，开发环境用 Vite proxy 转发 API

### 1.2 项目位置

- 后端: `backend/`
- 前端: `frontend/`（项目根目录下并列）

---

## 2. 技术栈

| 层面 | 选型 |
|------|------|
| 框架 | Vue 3 + TypeScript |
| 构建工具 | Vite |
| UI 组件库 | Element Plus |
| 状态管理 | Pinia |
| 路由 | Vue Router 4 |
| HTTP 客户端 | Axios |
| 包管理 | pnpm |

---

## 3. 架构方案：模块化单体 SPA

```
src/
├── app/                  # 应用入口、路由、全局状态、布局组件
│   ├── layouts/
│   │   ├── MainLayout.vue
│   │   ├── AppHeader.vue
│   │   └── AppSidebar.vue
│   └── router/
│       └── index.ts
│
├── modules/              # 功能模块（每个模块自包含）
│   ├── training/         # ✅ 训练任务管理
│   ├── template/         # ✅ 模板管理
│   ├── model-registry/   # ⏳ 预留骨架
│   └── auth/             # ⏳ 预留骨架
│
├── shared/               # 公共代码
│   ├── api/              # API 客户端封装
│   ├── components/       # 通用 UI 组件
│   ├── composables/      # 通用组合式函数
│   ├── stores/           # 全局 Pinia store
│   ├── types/            # 全局类型定义
│   └── utils/            # 工具函数
│
└── styles/               # 主题、全局样式
    ├── variables.scss     # CSS 变量（覆盖 Element Plus）
    ├── dark-overrides.scss
    ├── global.scss
    └── theme.css
```

### 3.1 模块内部结构（统一约定）

每个功能模块遵循相同结构：

```
modules/<name>/
├── components/       # 模块专属组件
├── composables/      # 模块专属逻辑
├── stores/           # 模块 Pinia store
├── types/            # 模块类型定义
├── routes.ts         # 模块路由配置
└── index.ts          # 统一导出
```

### 3.2 新增模块步骤

1. 在 `modules/` 下创建目录，按约定结构填充
2. 在 `app/router/index.ts` 中导入模块路由
3. 在 `AppSidebar.vue` 中添加导航项

---

## 4. 主题与 UI 设计系统

### 4.1 配色体系（参考 TrafficMind）

```css
:root {
  /* 背景 */
  --el-bg-color:          #070e22;
  --el-bg-color-page:     #0b1730;
  --el-bg-color-overlay:  #0e1d3d;

  /* 边框 */
  --el-border-color:       rgba(80, 140, 255, 0.18);
  --el-border-color-light: rgba(80, 140, 255, 0.35);

  /* 文字 */
  --el-text-color-primary:   #dbe6ff;
  --el-text-color-regular:   #8aa0cc;
  --el-text-color-secondary: #5f739c;

  /* 主题色 */
  --el-color-primary: #3b82f6;
  --color-cyan:       #28e0e0;
  --color-teal:       #22d3ee;

  /* 功能色 */
  --el-color-success: #36e08a;
  --el-color-warning: #ffb020;
  --el-color-danger:  #ff5a6e;

  /* 发光效果 */
  --glow-cyan: 0 0 18px rgba(40, 224, 224, 0.25);
}
```

### 4.2 全局样式特征

| 特征 | 实现 |
|------|------|
| 背景网格 | `body::before` 46px 蓝色半透明网格线 |
| 径向渐变 | 右上角 `radial-gradient` 光晕 |
| 圆角 | 统一 10-14px，卡片 14px |
| 发光 | 激活/悬停 `box-shadow: var(--glow-cyan)` |
| 字体 | `"Microsoft YaHei", "PingFang SC", sans-serif` |
| 等宽 | `Consolas` 用于数据/时间戳 |

### 4.3 Element Plus 深色适配

- `variables.scss`: 覆盖 Element Plus CSS 变量
- `dark-overrides.scss`: 组件级深色样式覆盖
- `global.scss`: 背景网格、字体、全局样式
- `theme.css`: TrafficMind 风格自定义样式

---

## 5. 布局与导航

### 5.1 整体布局

```
+----------------------------------------------------------+
|  HEADER (60px 固定)                                       |
|  Logo + 系统名 | 功能状态统计 | 🔒用户头像(预留) | 时钟    |
+----------+-----------------------------------------------+
|  SIDEBAR |  MAIN CONTENT                                 |
|  (220px) |  (弹性宽度)                                    |
|          |                                                |
|  导航菜单 |  <router-view />                               |
|          |                                                |
+----------+-----------------------------------------------+
```

- MainLayout: CSS Grid `grid-template-rows: 60px 1fr`，内容区 `grid-template-columns: 220px 1fr`
- Sidebar 可折叠，折叠后仅显示图标（56px 宽）
- Header 右侧预留用户头像下拉位置

### 5.2 导航菜单

```
├── 🎯 训练任务        /training           → 任务列表（含创建按钮）
├── 📋 模板管理        /template           → 模板浏览
├── ──────────────
├── 📦 模型仓库        /model-registry     → ⏳ 占位页
├── 🔒 用户管理        /auth               → ⏳ 占位页
```

### 5.3 路由

```typescript
const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/training',
    children: [
      // 训练任务
      { path: 'training',         name: 'TrainingList',   component: TaskListPage },
      { path: 'training/:id',     name: 'TrainingDetail', component: TaskDetailPage },
      // 模板管理
      { path: 'template',         name: 'TemplateList',   component: TemplateListPage },
      // 预留
      { path: 'model-registry',   name: 'ModelRegistry',  component: PlaceholderPage },
      { path: 'auth',             name: 'Auth',           component: PlaceholderPage },
    ]
  }
]
```

---

## 6. 训练任务模块（training）

对应后端 `/training` 接口。

### 6.1 任务列表页 TaskListPage

- 工具栏：状态筛选下拉 + 搜索输入 + "创建训练任务"按钮
- 表格列：任务名称、模板、状态、队列、创建时间、操作（查看详情）
- 底部分页：Element Plus el-pagination
- 数据来源：`GET /training`（分页 + 状态筛选）
- 点击行跳转详情页 `/training/:id`

### 6.2 任务详情页 TaskDetailPage

- 顶部：返回按钮 + 任务名称
- 基本信息卡片：任务名称、模板、状态、队列、ClearML ID、时间等
- 参数快照卡片：JSON 树形展示 `parameter_snapshot`
- 运行时信息卡片：JSON 树形展示 `runtime_snapshot`
- 结果摘要卡片：JSON 树形展示 `result_summary`
- 操作区（仅 `status=succeeded` 时 ONNX 导出可用）：
  - [🔄 导出为 ONNX] → 弹出 ConversionDrawer
  - [查看 ClearML 任务] → 新窗口打开 ClearML 链接
  - [📦 注册到模型仓库] → 预留按钮，当前 disabled

### 6.3 创建任务抽屉 CreateTaskDrawer

- 从右侧滑出（el-drawer）
- 任务名称（必填）
- 选择模板（下拉，调 `GET /training/create-meta` 获取）
- 选择队列（下拉，展示 Agent 在线状态）
- 模板参数（动态表单：选择模板后根据 `defaults` 生成 key-value 编辑器）
- 提交：`POST /training`
- 成功后关闭抽屉 + 刷新列表

### 6.4 ONNX 导出抽屉 ConversionDrawer

- 源任务信息展示（只读）
- 任务名称（自动填充 `{原任务名}-onnx`，可改）
- 目标队列（从 create-meta 获取）
- 转换参数（JSON 编辑器，默认 `{"opset_version": 12, "simplify": true}`）
- 提交：`POST /conversion/onnx`
- 成功后提示

### 6.5 模块文件结构

```
modules/training/
├── components/
│   ├── TaskListPage.vue
│   ├── TaskDetailPage.vue
│   ├── CreateTaskDrawer.vue
│   ├── ConversionDrawer.vue
│   └── TaskStatusTag.vue
├── composables/
│   └── useTrainingList.ts
├── stores/
│   └── training.ts
├── types/
│   └── index.ts
├── routes.ts
└── index.ts
```

---

## 7. 模板管理模块（template）

对应后端 `GET /training/create-meta` 返回的 `templates` 数据。只读展示。

### 7.1 模板列表页 TemplateListPage

- 卡片网格布局展示所有模板
- 每张卡片：模板名称、入口脚本、默认队列、关键默认参数预览
- 点击卡片弹出详情对话框

### 7.2 模板详情对话框 TemplateDetailDialog

- 基本信息：模板名称、显示名称、默认队列、入口脚本
- 运行时配置：启动器、工作目录、环境变量
- 产物配置表格：名称、角色、格式、路径
- 默认参数 JSON 展示
- "使用此模板创建任务"按钮：关闭对话框 → 跳转训练页并打开创建抽屉预选模板

### 7.3 模块文件结构

```
modules/template/
├── components/
│   ├── TemplateListPage.vue
│   ├── TemplateCard.vue
│   └── TemplateDetailDialog.vue
├── composables/
│   └── useTemplates.ts
├── stores/
│   └── template.ts
├── types/
│   └── index.ts
├── routes.ts
└── index.ts
```

---

## 8. 预留模块

### 8.1 模型仓库（model-registry）

- 路由占位：`/model-registry`
- 空页面显示"功能开发中"
- 类型定义占位：ModelFamily、ModelVersion、ModelFile 接口
- 等后端 model_registry API 就绪后填充

### 8.2 用户管理（auth）

- 路由占位：`/auth`
- 空页面显示"功能开发中"
- 类型定义占位：User、Role、Permission 接口
- 等后端 IAM 模块就绪后填充

两个预留模块均遵循统一模块结构（components/composables/stores/types/routes.ts/index.ts），扩展时零侵入。

---

## 9. 公共层设计（shared）

### 9.1 API 客户端

```
shared/api/
├── client.ts           # axios 实例 + 拦截器
├── types.ts            # ApiEnvelope<T>, PaginationParams, PaginatedData<T>
└── modules/
    ├── training.ts     # getTrainingList, getTrainingDetail, getCreateMeta, createTraining
    ├── conversion.ts   # createOnnxConversion
    └── system.ts       # getHealth, getRuntime
```

**client.ts 职责：**
- baseURL 从环境变量或 Vite proxy 读取
- 请求拦截：注入 request_id
- 响应拦截：解包 Envelope（code/message/data），统一错误处理（ElMessage 提示）
- 后端响应格式：
  - 成功: `{ code: 0, message: "success", data: T, request_id, warnings }`
  - 失败: `{ code: non-zero, message, details, request_id }`

### 9.2 通用组件

| 组件 | 说明 |
|------|------|
| PageHeader.vue | 页面标题栏（标题 + 描述 + 操作按钮插槽） |
| JsonViewer.vue | JSON 树形展示（参数快照、运行时信息等） |
| StatusTag.vue | 通用状态标签（颜色映射） |
| EmptyState.vue | 空状态占位 |
| PlaceholderPage.vue | "功能开发中"占位页 |

### 9.3 通用组合式函数

| 函数 | 说明 |
|------|------|
| usePagination | 分页逻辑（page, pageSize, total, onPageChange） |
| useLoading | 加载状态管理（loading, withLoading 包装器） |

### 9.4 全局 Store

- `app.ts`: 侧边栏折叠状态等全局 UI 状态

### 9.5 工具函数

- `format.ts`: 时间格式化、文件大小格式化
- `constants.ts`: 状态枚举映射、状态颜色映射

---

## 10. Vite 配置

### 10.1 开发代理

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:18087',
      changeOrigin: true,
    }
  }
}
```

### 10.2 路径别名

```typescript
resolve: {
  alias: {
    '@': '/src',
  }
}
```

---

## 11. V1 不做的事

- ❌ 不造 mock 数据、不做数据模拟
- ❌ 不实现模型仓库页面功能（等后端 API）
- ❌ 不实现用户/角色/权限（等后端 IAM）
- ❌ 不实现仪表盘/系统监控页面
- ❌ 不做国际化（仅中文）

---

## 12. 后续扩展路线

| 阶段 | 前端新增内容 |
|------|-------------|
| Phase 2 | 模型仓库完整页面（模型族列表、版本管理、文件管理、注册流程） |
| Phase 3 | 更多转换格式（海思/联咏/RKNN）、文件血缘可视化 |
| Phase 4 | 评测任务页面、调试预测页面 |
| Phase 5 | 用户登录、角色权限管理 |
