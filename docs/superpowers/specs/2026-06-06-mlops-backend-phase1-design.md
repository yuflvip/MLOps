# MLOps Backend Phase 1 Design

## 1. 目标

一期后端建设目标是落地一个可运行的 MLOps 平台后端骨架，并打通以下最小业务闭环：

- 平台内基于 YAML 模板创建训练任务。
- 将训练任务下发为 ClearML task。
- 定时同步训练任务和导出任务状态到本地数据库。
- 在训练任务详情页基于训练任务派生 `PT -> ONNX` 导出 `child task`。
- 展示训练任务、导出任务及其产物信息。

## 2. 一期范围

一期只实现以下可运行模块：

- `training`
- `conversion`
- `sync`
- `system`

以下能力仅保留扩展位，不进入一期主流程：

- `model_registry`
- `evaluation`
- `edge_inference`
- `iam`
- 独立的 `parameter_template` 业务模块

## 3. 核心设计决策

### 3.1 数据建模

- 一期采用统一任务表方案。
- 核心主表为 `tasks`。
- 核心产物表为 `task_artifacts`。
- 不在一期拆分 `training_task`、`conversion_task`、`model_file` 等独立业务表。

### 3.2 任务关系

- 训练任务使用：
  - `task_group = training`
  - `task_type = training`
- ONNX 导出任务使用：
  - `task_group = export`
  - `task_type = export_onnx`
- 导出任务通过 `parent_task_id` 指向来源训练任务。
- 导出产物可通过 `parent_artifact_id` 关联来源 PT 文件。

### 3.3 模板体系

- 一期模板采用 YAML 配置方案。
- 模板不落库。
- 后端负责读取模板、合并默认值、渲染参数、执行基础校验。
- 模板需要至少覆盖：
  - 模板名称
  - 模板类型
  - 默认参数
  - 运行环境信息
  - 执行目录
  - 入口命令
  - 默认队列

### 3.4 ClearML 队列与 Agent 可观测性

- 创建训练任务前，页面需要看到模板列表、可用队列和队列在线状态摘要。
- Agent 在线状态通过实时查询 ClearML 获取，不单独建设本地快照表。
- 目标队列没有在线 Agent 时，允许提交训练任务。
- 提交接口必须返回明确 `warning`，提示任务将在 Agent 上线后自动领取。
- 一期不支持指定某一台训练机执行任务，平台只选择队列。

## 4. 模块职责

### 4.1 training

- 训练任务列表查询
- 训练任务详情查询
- 训练创建元数据查询
- 创建训练任务

### 4.2 conversion

- 从训练任务派生 ONNX 导出任务
- 查询导出任务详情和结果摘要

### 4.3 sync

- 同步运行中训练任务
- 同步已完成训练任务
- 同步运行中导出任务
- 同步失败补偿与重放
- 维护 `sync_checkpoints` 和 `job_runs`

### 4.4 system

- 健康检查
- 系统配置摘要
- 调度器状态
- ClearML 队列和 Agent 状态查询

## 5. 服务层设计

- `TaskQueryService`
  - 提供统一任务列表和任务详情查询
- `TrainingCommandService`
  - 创建训练任务
- `ConversionCommandService`
  - 创建 ONNX 导出任务
- `ClearMLSyncService`
  - 同步 ClearML task 到本地统一任务模型
- `TemplateService`
  - 读取 YAML 模板并渲染参数
- `SchedulerService`
  - 注册并触发同步作业

## 6. 一期接口方向

建议一期至少预留以下 API：

- `GET /training`
- `GET /training/{task_id}`
- `GET /training/create-meta`
- `POST /training`
- `POST /conversion/onnx`
- `GET /system/health`
- `GET /system/runtime`
- `GET /system/clearml/queues`
- `GET /system/clearml/agents`

### 6.1 REST API 统一约定

- 所有业务接口统一使用 REST 风格命名，资源路径使用名词，不在路径中混入动词式私有命名。
- 成功响应统一返回：
  - `code`
  - `message`
  - `data`
  - `request_id`
  - `warnings`
- 失败响应统一返回：
  - `code`
  - `message`
  - `details`
  - `request_id`
- 列表接口统一在 `data` 中返回：
  - `items`
  - `total`
  - `page`
  - `page_size`
- 当目标队列无在线 Agent 但允许提交训练任务时，需通过 `warnings` 返回提示，而不是改变成功响应结构。
- 健康检查接口可简化，但字段命名仍应保持一致风格。

## 7. 数据字段补充要求

`tasks` 表一期除基础字段外，应重点包含：

- `task_group`
- `task_type`
- `parent_task_id`
- `queue_name`
- `template_name`
- `params_json`
- `parameter_snapshot_json`
- `runtime_snapshot_json`
- `custom_data_json`
- `result_summary_json`
- `last_sync_time`
- `last_sync_status`
- `last_sync_error`

`task_artifacts` 表一期需要支持：

- 一个任务多个产物
- 导出产物和训练产物的血缘关联
- ClearML artifact 和 output model 关联字段

## 8. 一期骨架要求

后端骨架至少应包含：

- FastAPI 应用入口
- 配置加载体系
- 日志初始化
- SQLAlchemy 基础设施
- Alembic 初始化结构
- 统一 ORM 模型
- 仓储接口与基础实现
- ClearML adapter 接口占位
- 调度器启动与作业注册占位
- 路由、schema、service、repository、domain 的基础分层

## 9. 非目标

以下内容不作为一期骨架必须交付：

- 模型仓库完整能力
- 模板管理界面
- 用户、角色、权限系统
- 指定单机执行策略
- 实时日志代理
- 对象存储抽象
- Worker 独立进程

## 10. 实施注意点

- 路由层不直接操作数据库。
- 调度作业只调用应用服务层。
- ClearML 细节不泄漏到 API 层响应模型。
- 所有同步逻辑必须幂等。
- SQLite 是一期数据库，但目录结构和配置应保留迁移 PostgreSQL 的空间。

## 11. 当前已知风险

- ClearML Agent/Queue 的实际查询字段需要在接入时根据现有 ClearML 版本确认。
- YAML 模板结构需要在骨架阶段尽快固定，否则训练创建接口会反复调整。
- 当前工作区不是 Git 仓库，设计文档无法按标准流程提交 commit，只能先保存到本地文档中。
