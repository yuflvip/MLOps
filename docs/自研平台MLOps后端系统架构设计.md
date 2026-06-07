# 自研平台 MLOps 后端系统架构设计

## 1. 文档目标

本文档用于指导自研平台 MLOps 后端系统的一期建设与后续扩展，目标如下：

- 基于 `Python 3.12` 与项目内 `.venv` 构建后端服务。
- 采用 `模块化单体 + 内嵌调度 + 共享服务层直调` 架构。
- 以 `SQLite` 作为一期数据库，满足本地开发、小规模部署和 MVP 验证需求。
- 保证模块边界清晰、功能耦合度低、配置外置、便于后续平滑演进。
- 一期优先打通“训练类任务同步 + PT 导出 ONNX 闭环”，同时为模型仓库、格式转换、评测、推理等后续能力预留扩展点。

本文档重点描述：

- 后端总体架构与模块划分
- 运行形态与配置体系
- 数据库表设计与字段中文说明
- ClearML 集成方式
- 调度、同步、日志、异常处理设计
- 一期落地范围与后续演进路径

### 1.1 一期已确认落地边界

经当前阶段讨论，一期范围补充确认如下：

- 一期除“训练类任务同步 + PT 导出 ONNX 闭环”外，还包含“平台内新建训练任务”能力。
- 一期数据建模采用统一任务表方案，以 `tasks` 和 `task_artifacts` 作为核心主数据结构，不在一期拆分 `training_task`、`conversion_task`、`model_file` 等独立业务表。
- `PT -> ONNX` 导出任务采用基于训练任务派生 `child task` 的关系模型，导出任务通过 `parent_task_id` 关联来源训练任务。
- 一期模板采用“配置版”方案，模板写入 YAML 配置，由后端读取、渲染和校验，不落库。
- 一期仅实现 `training`、`conversion`、`sync`、`system` 四个可运行模块；`model_registry`、`evaluation`、`iam` 等仅保留扩展位，不进入一期主流程。
- 页面创建训练任务时，需要展示 ClearML 队列和 Agent 在线状态；当目标队列当前没有在线 Agent 时，平台允许提交任务，但必须明确返回告警信息。

---

## 2. 架构目标与设计原则

### 2.1 架构目标

自研平台后端需要同时满足以下要求：

- 对业务人员提供统一的中文化平台入口。
- 不直接暴露 ClearML 原始对象，而是沉淀平台自己的业务模型。
- 将训练、导出、转换、评测、模型资产管理等能力逐步统一到一个平台中。
- 让任务执行、实验留痕、日志、指标、产物管理继续由 ClearML 承担。
- 避免在平台后端通过 `subprocess` 长时间执行训练、导出、转换任务。
- 在不引入过早复杂度的前提下，为后续拆分 Worker、迁移 PostgreSQL、接入对象存储和消息队列做好准备。

### 2.2 设计原则

1. **模块化单体**
   - 一期采用单体部署，降低实现成本和运维复杂度。
   - 在代码结构上严格按模块划分，避免单体代码失控膨胀。

2. **共享服务层直调**
   - API、调度任务、补偿任务统一调用应用服务层。
   - 避免路由直接操作数据库，也避免仓储层反向依赖业务层。

3. **配置外置**
   - API 服务端口、根路径、调度周期、ClearML 连接信息、日志策略等均应通过配置文件管理。
   - 敏感信息通过 `.env` 覆盖，不写死在代码中。

4. **平台模型优先**
   - ClearML 是底层执行与实验追踪引擎，不是最终业务模型。
   - 平台必须维护自己的任务、模型文件、同步状态等主数据。

5. **幂等、可补偿、可追踪**
   - 同步任务必须支持重复执行不产生重复数据。
   - 同步失败后可重试、可回放、可追踪。

6. **易扩展**
   - 一期使用 SQLite，但数据库访问层和配置层需预留迁移能力。
   - 内嵌调度器未来可拆成独立进程，不推翻业务模块。

---

## 3. 技术栈选型

### 3.1 基础技术栈

- Python：`3.12`
- 虚拟环境：项目根目录 `.venv`
- Web 框架：`FastAPI`
- 数据校验与配置：`Pydantic v2`
- ORM：`SQLAlchemy 2.x`
- 数据库迁移：`Alembic`
- 调度器：`APScheduler`
- HTTP 客户端：`httpx`
- 日志：`logging` + `TimedRotatingFileHandler` 或结构化 JSON Handler
- 测试：`pytest`

### 3.2 选型理由

1. `FastAPI`
   - 适合快速构建后台 API。
   - 与 Pydantic、OpenAPI 集成成熟。
   - 生命周期钩子适合初始化调度器与系统资源。

2. `SQLAlchemy 2.x`
   - 支持清晰的仓储层封装。
   - 后续从 SQLite 迁移 PostgreSQL 成本较低。

3. `APScheduler`
   - 支持 Cron 表达式。
   - 适合实现内嵌调度能力。
   - 后续可抽象为独立 Scheduler 进程而不改变业务服务接口。

4. `SQLite`
   - 一期轻量、部署成本低。
   - 适合 MVP、本地调试和中小规模后台场景。
   - 通过分层设计降低未来迁移 PostgreSQL 的成本。

---

## 4. 总体架构设计

### 4.1 总体定位

本系统采用：

```text
模块化单体 + 内嵌调度 + 共享服务层直调
```

运行上仅启动一个 API 进程，但逻辑上划分为：

- HTTP API 接口层
- 应用服务层
- 领域模型层
- 基础设施层
- 内嵌调度层

### 4.2 总体交互关系

```text
前端页面
  ↓ HTTP
MLOps 后端 API
  ├── 应用服务层
  │     ├── 任务服务
  │     ├── 转换任务服务
  │     ├── ClearML 同步服务
  │     ├── 模型仓库服务（后续）
  │     └── 系统配置/调度服务
  │
  ├── 基础设施层
  │     ├── SQLite
  │     ├── ClearML Adapter
  │     ├── 调度器封装
  │     ├── 日志组件
  │     └── 配置加载器
  │
  └── 内嵌调度器
        ├── 定时同步训练类任务
        ├── 定时同步导出类任务
        ├── 同步失败补偿
        └── 作业运行记录
```

### 4.3 与 ClearML 的边界

#### 自研平台负责

- 中文化业务入口
- 业务数据模型
- 任务列表、详情、筛选、搜索
- 导出 ONNX 等业务操作入口
- 模型资产管理入口
- 状态聚合展示
- 业务状态流转与平台规则控制

#### ClearML 负责

- Task 执行记录
- Agent 调度与队列执行
- 实验日志
- 训练参数与指标
- Artifacts 和 OutputModel
- 原始实验留痕

#### 结论

平台后端不直接执行长耗时模型任务，而是：

- 创建或查询 ClearML 任务
- 同步任务状态
- 读取产物信息
- 将结果转换为平台自己的业务模型供前端展示

---

## 5. 分层架构设计

### 5.1 Interface 层

职责：

- 提供 REST API
- 请求参数校验
- 响应结构序列化
- 异常到 HTTP 状态码映射
- 提供健康检查与系统状态查询
- 保持统一的响应包裹格式与错误返回格式

建议内容：

- `routers`
- `schemas`
- `deps`
- `errors`

接口风格约定：

- 路由命名采用 REST 风格，以资源为中心组织路径。
- 成功响应建议统一包含 `code`、`message`、`data`、`request_id`、`warnings`。
- 失败响应建议统一包含 `code`、`message`、`details`、`request_id`。
- 列表接口建议在 `data` 中统一返回 `items`、`total`、`page`、`page_size`。

### 5.2 Application 层

职责：

- 编排业务用例
- 调用多个仓储和适配器完成业务流程
- 管理事务边界
- 作为 API 与调度任务的统一服务入口

典型服务：

- `TaskQueryService`
- `TrainingCommandService`
- `ConversionCommandService`
- `ClearMLSyncService`
- `TemplateService`
- `SchedulerService`
- `ModelRegistryService`（后续）

### 5.3 Domain 层

职责：

- 沉淀业务核心概念
- 定义状态机和领域规则
- 提供与框架无关的业务模型与异常

典型内容：

- 任务状态枚举
- 模型文件状态枚举
- 状态流转规则
- 唯一性与合法性校验规则

### 5.4 Infrastructure 层

职责：

- 数据库访问与仓储实现
- ClearML SDK 或 API 封装
- 调度器封装
- 配置加载
- 日志初始化
- 文件与存储适配

典型内容：

- `db`
- `repositories`
- `clearml`
- `scheduler`
- `config`
- `logging`

---

## 6. 模块划分设计

### 6.1 一期核心模块

#### 1. 训练任务模块 `training`

职责：

- 管理训练类任务列表与详情
- 处理平台内训练任务发起与结果展示
- 基于 YAML 模板回填默认参数、运行环境和目标队列
- 在创建训练任务前展示目标队列及 Agent 在线状态
- 展示 ClearML 训练任务的聚合结果

#### 2. 转换任务模块 `conversion`

职责：

- 一期仅实现 `PT -> ONNX` 导出任务
- 从训练任务派生 ONNX 导出 `child task`
- 处理导出任务发起与结果展示
- 跟踪任务状态、失败原因、产物信息

#### 3. 同步模块 `sync`

职责：

- 定时从 ClearML 拉取任务数据
- 写入或更新本地数据库
- 负责补偿同步、重放同步和同步状态跟踪

#### 4. 系统模块 `system`

职责：

- 管理配置读取
- 管理调度器初始化与作业注册
- 提供健康检查、系统配置查看、运行状态查看
- 提供 ClearML 队列与 Agent 在线状态查询
- 预留登录认证、用户上下文、权限校验、操作审计等系统能力接入点

### 6.2 后续扩展模块

#### 5. 模型仓库模块 `model_registry`

职责：

- 管理模型族
- 管理模型版本
- 管理模型文件及其血缘关系

#### 6. 参数模板模块 `parameter_template`

职责：

- 当前阶段不作为独立业务模块落地
- 一期仅保留模板渲染与校验能力，模板源头为 YAML 配置
- 后续如需模板管理界面，再演进为独立模块和独立数据表

#### 7. 评测模块 `evaluation`

职责：

- 管理评测任务
- 保存评测指标
- 支持版本或文件级评测记录

#### 8. 边缘推理模块 `edge_inference`

职责：

- 提供调试预测入口
- 对接边缘推理服务结果
- 保存少量预测样例和结果摘要

#### 9. 身份与访问控制预留模块 `iam`

职责预留：

- 预留登录认证能力接入位置
- 预留用户、角色、权限的模块边界
- 预留请求级用户上下文注入能力
- 预留接口权限与关键操作权限校验能力
- 预留操作审计与安全日志能力

说明：

- 当前阶段不展开 IAM 详细设计。
- 当前阶段不单独拆分独立认证服务。
- 架构上仅要求预留可插拔扩展点，避免后续重构核心业务模块。

---

## 7. 目录结构建议

建议后端目录结构如下：

```text
backend/
  app/
    main.py
    api/
      routers/
        training.py
        conversion.py
        system.py
      schemas/
      deps/
      errors/
      auth/
    application/
      services/
        task_query_service.py
        training_command_service.py
        conversion_command_service.py
        clearml_sync_service.py
        template_service.py
        scheduler_service.py
      dto/
    domain/
      common/
        enums.py
        exceptions.py
      training/
      conversion/
      sync/
      iam/
    infrastructure/
      config/
        settings.py
        loader.py
      db/
        base.py
        session.py
        models.py
      repositories/
        task_repository.py
        task_artifact_repository.py
        sync_checkpoint_repository.py
        job_run_repository.py
      clearml/
        adapter.py
        clients.py
        mapper.py
        queue_probe.py
      template/
        renderer.py
        validator.py
      scheduler/
        manager.py
        jobs.py
      logging/
        setup.py
        context.py
      auth/
        providers.py
        context.py
    bootstrap/
      container.py
      lifespan.py
  migrations/
  tests/
  config/
    app.yaml
    app.local.yaml
  pyproject.toml
  .env.example
```

说明：

- 一期只创建可运行主链路所需文件；`model_registry`、`evaluation`、`parameter_template` 等后续模块不在一期骨架中生成空服务和空仓储。
- 查询接口优先通过统一任务查询服务实现，避免训练任务与导出任务各自维护一套重复列表逻辑。

---

## 8. 运行形态设计

### 8.1 一期运行方式

一期采用单进程运行：

- 一个 `FastAPI` 进程承载 API 服务
- API 生命周期中初始化调度器
- 调度器在后台线程中执行同步与补偿任务

### 8.2 设计要求

即使是一体化运行，也应满足：

- 调度作业不直接依赖路由层
- 调度作业调用应用服务层
- 调度器管理代码与业务服务代码解耦
- 作业定义与 Cron 配置分离

### 8.3 后续演进方式

后续可平滑拆分为：

- `api`：提供外部 HTTP 服务
- `scheduler`：专门执行定时同步和补偿
- `worker`：专门执行平台内部异步作业

由于业务入口统一经过应用服务层，拆分时无需重写核心业务逻辑。

---

## 9. 配置体系设计

### 9.1 配置来源

建议采用：

- `config/app.yaml`：默认配置
- `config/app.local.yaml`：本地或环境覆盖配置
- `.env`：敏感信息和环境变量
- CLI 参数：最终覆盖启动项

优先级如下：

```text
默认值 < app.yaml < app.local.yaml < .env < CLI 参数
```

### 9.2 配置分类

配置建议至少分为以下部分：

- `app`
- `auth`
- `database`
- `clearml`
- `scheduler`
- `logging`
- `features`

### 9.3 配置项示例

```yaml
app:
  name: "mlops-backend"
  env: "dev"
  debug: true
  host: "0.0.0.0"
  port: 18087
  root_path: "/api"
  docs_url: "/docs"
  openapi_url: "/openapi.json"
  timezone: "Asia/Shanghai"

auth:
  enabled: false
  mode: "disabled"
  jwt_secret: "${JWT_SECRET}"
  token_expire_minutes: 120
  allow_anonymous: true

database:
  url: "sqlite:///./data/mlops.db"
  echo: false
  pool_pre_ping: true

clearml:
  api_server: "http://127.0.0.1:8008"
  web_server: "http://127.0.0.1:8080"
  files_server: "http://127.0.0.1:8081"
  access_key: "${CLEARML_ACCESS_KEY}"
  secret_key: "${CLEARML_SECRET_KEY}"
  verify_ssl: false
  request_timeout_seconds: 30
  default_project: "MLOps"
  queue:
    train_gpu: "queue_train_gpu"
    export_onnx: "queue_export_onnx"
  template_sources:
    training: "./config/training-templates.yaml"
    conversion: "./config/conversion-templates.yaml"

scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  single_instance_only: true
  jobs:
    sync_running_training_tasks:
      enabled: true
      cron: "0 */1 * * *"
      max_instances: 1
      coalesce: true
      misfire_grace_time: 60
    sync_finished_training_tasks:
      enabled: true
      cron: "30 */5 * * *"
    sync_running_export_tasks:
      enabled: true
      cron: "15 */1 * * *"
    retry_failed_sync:
      enabled: true
      cron: "0 */10 * * *"

logging:
  level: "INFO"
  format: "json"
  file_enabled: true
  file_path: "./logs/app.log"
  access_log: true
  sql_log: false
  rotate:
    when: "midnight"
    backup_count: 14

features:
  enable_swagger: true
  enable_scheduler: true
  enable_model_registry: false
```

### 9.4 配置设计要求

#### API 配置

必须支持：

- 服务地址 `host`
- 服务端口 `port`
- 根路径 `root_path`
- 文档路径 `docs_url`
- OpenAPI 路径 `openapi_url`

#### ClearML 配置

必须支持：

- API 服务地址
- Web 服务地址
- 文件服务地址
- Access Key / Secret Key
- SSL 校验开关
- 超时参数
- 默认项目
- 队列名称映射
- 队列与 Agent 状态查询能力
- YAML 模板文件路径

#### 调度配置

必须支持：

- 全局开关
- 单实例运行约束
- 时区
- 每个作业单独开关
- Cron 表达式
- 并发限制
- 丢失触发补偿参数

#### 日志配置

必须支持：

- 日志级别
- 输出格式
- 文件输出开关
- 文件路径
- 文件轮转策略
- 是否输出 Access Log
- 是否输出 SQL 日志

#### 认证配置预留

当前阶段即使不实现完整 IAM，也建议预留：

- `auth.enabled`
- `auth.mode`
- `auth.jwt_secret`
- `auth.token_expire_minutes`
- `auth.allow_anonymous`

说明：

- 一期可以默认关闭认证或允许匿名访问。
- 后续接入 JWT、LDAP、OIDC 或独立认证中心时，不需要推翻配置体系。
- 调度器在一期架构下仅允许单实例开启，多实例部署时应关闭非主实例上的调度器。

---

## 10. 数据库设计总览

### 10.1 设计原则

1. 一期数据库以业务展示与任务编排为目标，不直接镜像 ClearML 所有字段。
2. 外部系统主键与本地主键分离。
3. JSON 类扩展字段统一使用 `TEXT` 存储，避免一开始过度拆表。
4. 所有同步表都必须具备幂等更新能力。
5. 表结构预留模型仓库扩展空间。
6. 表结构应预留未来接入认证、用户、审计体系所需的扩展字段和关联能力。

### 10.2 一期必需表

一期建议建设以下核心表：

- `tasks`：统一任务表
- `task_artifacts`：任务产物表
- `sync_checkpoints`：同步检查点表
- `job_runs`：调度作业运行表

### 10.3 后续预留表

- `model_families`：模型族表
- `model_versions`：模型版本表
- `model_files`：模型文件表
- `parameter_templates`：参数模板表
- `device_types`：设备类型表
- `operation_logs`：操作日志表

---

## 11. 数据表详细设计

## 11.1 tasks 统一任务表

### 表作用

用于保存平台侧所有任务主数据，是任务列表页、任务详情页、任务状态同步、任务血缘追踪的核心主表。

该表的职责是：

- 保存所有任务的公共骨架字段
- 保存任务状态与同步状态
- 保存任务参数快照和运行环境快照
- 保存任务类型特有扩展字段
- 建立本地任务与 ClearML Task 的关联
- 建立任务上下游血缘关系
- 支撑全局任务列表、筛选、搜索与详情展示

### 一期任务承载约定

- 训练任务：
  - `task_group = training`
  - `task_type = training`
- ONNX 导出任务：
  - `task_group = export`
  - `task_type = export_onnx`
  - `parent_task_id` 指向来源训练任务
- 平台内创建的任务在创建时先落本地库，再关联 ClearML 返回的 `clearml_task_id`
- 训练详情页发起导出时，应继承训练任务必要上下文，并生成新的导出类 `child task`

### 字段设计

| 字段名 | 类型 | 是否必填 | 中文名称 | 字段说明 |
|---|---|---:|---|---|
| `id` | INTEGER | 是 | 主键 ID | 平台内部主键，自增标识。 |
| `model_family_id` | INTEGER | 否 | 模型族 ID | 关联 `model_families.id`，表示该任务归属哪个模型族。 |
| `parent_task_id` | INTEGER | 否 | 父任务 ID | 一期主要用于导出等派生 `child task` 关联，ONNX 导出任务指向来源训练任务。 |
| `task_source` | VARCHAR(32) | 是 | 任务来源 | 任务来源类型，建议取值为 `clearml/platform/internal`。 |
| `clearml_task_id` | VARCHAR(128) | 否 | ClearML 任务 ID | 对应 ClearML 中任务的唯一标识；仅当任务来源为 `clearml` 时填写。 |
| `clearml_project_id` | VARCHAR(128) | 否 | ClearML 项目 ID | 对应 ClearML 项目标识，用于辅助定位来源项目。 |
| `task_name` | VARCHAR(255) | 是 | 任务名称 | 平台展示的训练任务名称。 |
| `task_type` | VARCHAR(64) | 是 | 任务类型 | 任务细粒度类型，如 `training`、`export_onnx`、`export_hisi3403`、`quantize_rknn`。 |
| `task_group` | VARCHAR(32) | 是 | 任务分组 | 一期必填，用于统一列表分类与筛选，建议取值如 `training/export/quantization/evaluation/prediction`。 |
| `model_type` | VARCHAR(64) | 否 | 模型类型 | 分类、检测、OCR 等业务模型类型。 |
| `status` | VARCHAR(32) | 是 | 任务状态 | 任务状态，取值建议为 `queued/running/succeeded/failed/cancelled`。 |
| `owner` | VARCHAR(128) | 否 | 任务负责人 | 任务发起人或任务归属人。 |
| `queue_name` | VARCHAR(128) | 否 | 目标队列名称 | 记录任务投递到的 ClearML 队列名称。 |
| `template_name` | VARCHAR(128) | 否 | 模板名称 | 记录创建任务时使用的 YAML 模板名称。 |
| `params_json` | TEXT | 否 | 参数 JSON | 用户提交参数或模板默认参数的业务视角值。 |
| `runtime_snapshot_json` | TEXT | 否 | 运行环境快照 JSON | 记录本次任务实际使用的环境、执行目录、入口命令、目标队列等快照。 |
| `parameter_snapshot_json` | TEXT | 否 | 参数快照 JSON | 记录本次任务实际执行的完整参数快照，防止模板变更影响历史任务还原。 |
| `custom_data_json` | TEXT | 否 | 自定义扩展 JSON | 存储任务类型特有字段，如数据集版本、目标格式、量化参数、预测输入信息等。 |
| `result_summary_json` | TEXT | 否 | 结果摘要 JSON | 存储任务结果摘要，如关键指标、导出结果、输出统计、评测摘要等。 |
| `started_at` | DATETIME | 否 | 开始时间 | 任务开始执行时间。 |
| `completed_at` | DATETIME | 否 | 完成时间 | 任务结束时间。 |
| `error_message` | TEXT | 否 | 错误信息 | 任务失败时的摘要错误信息。 |
| `clearml_task_url` | VARCHAR(512) | 否 | ClearML 页面地址 | 对应 ClearML 任务详情页链接。 |
| `raw_summary_json` | TEXT | 否 | 原始摘要 JSON | 从 ClearML 同步来的原始摘要信息，用于兼容后续展示扩展。 |
| `last_sync_time` | DATETIME | 否 | 最后同步时间 | 本条记录最近一次成功同步的时间。 |
| `last_sync_status` | VARCHAR(32) | 否 | 最后同步状态 | 最近一次同步结果，如 `success/failed`。 |
| `last_sync_error` | TEXT | 否 | 最后同步错误 | 最近一次同步失败的错误原因。 |
| `sync_version` | INTEGER | 是 | 同步版本号 | 用于控制重复同步和并发更新，默认从 1 开始。 |
| `created_by` | VARCHAR(128) | 否 | 创建人 | 预留给后续认证系统，用于记录创建该任务的用户标识。 |
| `updated_by` | VARCHAR(128) | 否 | 更新人 | 预留给后续认证系统，用于记录最后更新该任务的用户标识。 |
| `owner_id` | VARCHAR(128) | 否 | 归属人 ID | 预留给后续认证系统，用于记录任务归属用户标识。 |
| `created_at` | DATETIME | 是 | 创建时间 | 本地记录创建时间。 |
| `updated_at` | DATETIME | 是 | 更新时间 | 本地记录更新时间。 |

### 约束建议

- `clearml_task_id` 在非空时唯一
- `task_source` 建议建立普通索引
- `task_type` 建议建立普通索引
- `task_group` 建议建立普通索引
- `task_name` 建议建立普通索引
- `status` 建议建立普通索引
- `owner` 建议建立普通索引
- `queue_name` 建议建立普通索引
- `model_family_id` 建议建立普通索引
- `parent_task_id` 建议建立普通索引
- `started_at`、`completed_at` 建议建立时间索引

### `task_type` 命名建议

建议直接采用细粒度类型值，避免后续再拆“主类型 + 子类型”：

- `training`
- `export_onnx`
- `export_hisi3403`
- `export_novatek692`
- `quantize_rknn`
- `quantize_hisi3403`
- `evaluate_accuracy`
- `evaluate_performance`
- `predict_debug_image`

### `custom_data_json` 使用规范

`custom_data_json` 用于存储任务类型特有字段，但不能替代公共查询字段。

建议放入：

- 训练任务的 `dataset_version`、`best_metric`、`metrics_summary`
- 导出任务的 `source_artifact_id`、`target_format`、`opset`、`dynamic`、`simplify`
- 量化任务的 `calib_dataset`、`quant_method`、`input_layout`
- 预测任务的 `input_type`、`input_uri`、`threshold`

不建议放入：

- `task_name`
- `task_type`
- `status`
- `clearml_task_id`
- `task_source`
- `started_at`
- `completed_at`

这些字段必须结构化落表，否则后续列表筛选、排序、统计都会变得困难。

### `custom_data_json` 示例

导出 ONNX 任务：

```json
{
  "source_artifact_id": 123,
  "target_format": "onnx",
  "opset": 12,
  "dynamic": true,
  "simplify": true
}
```

训练任务：

```json
{
  "dataset_version": "dataset_v4",
  "best_metric": "mAP=0.942",
  "metrics_summary": {
    "mAP50": 0.942,
    "precision": 0.913
  }
}
```

### 创建训练任务与队列可观测性约定

- 页面发起训练前，后端应提供训练创建所需元数据接口，返回模板列表、可选队列以及各队列在线状态摘要。
- 队列与 Agent 状态一期通过实时查询 ClearML 获取，不在本地数据库中单独建设 `agents` 或 `queues` 快照表。
- 若目标队列当前没有在线 Agent，平台允许创建训练任务，但接口必须返回显式 `warning` 信息，提示任务将在 Agent 上线后自动领取。
- 任务与执行机器的关系以队列为主，不在一期设计中支持“指定某一台训练机执行”的平台级调度逻辑。

---

## 11.2 task_artifacts 任务产物表

### 表作用

用于统一管理各类任务产生的文件产物。

设计该表的原因：

- 避免把文件字段硬编码在 `tasks` 表中
- 支持一个任务产生多个文件
- 支持文件血缘关系
- 为模型仓库阶段复用文件资产数据打基础

### 字段设计

| 字段名 | 类型 | 是否必填 | 中文名称 | 字段说明 |
|---|---|---:|---|---|
| `id` | INTEGER | 是 | 主键 ID | 平台内部主键，自增标识。 |
| `owner_type` | VARCHAR(32) | 是 | 所属对象类型 | 表示产物归属对象类型，当前统一建议使用 `task`。 |
| `owner_id` | INTEGER | 是 | 所属对象 ID | 对应归属对象的本地主键 ID。 |
| `artifact_name` | VARCHAR(255) | 是 | 产物名称 | 文件名称，如 `best.pt`、`best.onnx`。 |
| `artifact_type` | VARCHAR(64) | 是 | 产物类型 | 文件类型，如 `pt`、`onnx`、`om`、`rknn`、`json`、`txt`。 |
| `storage_uri` | VARCHAR(512) | 否 | 存储地址 | 文件在 ClearML、对象存储或本地存储中的地址。 |
| `clearml_artifact_key` | VARCHAR(255) | 否 | ClearML 产物 Key | ClearML Artifact 或 OutputModel 的键值标识。 |
| `clearml_model_id` | VARCHAR(128) | 否 | ClearML 模型 ID | 对应 ClearML OutputModel 标识。 |
| `parent_artifact_id` | INTEGER | 否 | 父产物 ID | 指向来源文件，用于表示文件血缘，如 ONNX 的父文件是 PT。 |
| `status` | VARCHAR(32) | 是 | 产物状态 | 建议取值为 `pending/ready/failed/deleted`。 |
| `size_bytes` | BIGINT | 否 | 文件大小 | 文件字节数。 |
| `checksum` | VARCHAR(128) | 否 | 校验值 | 文件校验值，如 md5、sha256。 |
| `metadata_json` | TEXT | 否 | 元数据 JSON | 产物补充信息，如框架、设备、标签文件等。 |
| `created_at` | DATETIME | 是 | 创建时间 | 本地记录创建时间。 |
| `updated_at` | DATETIME | 是 | 更新时间 | 本地记录更新时间。 |

### 约束建议

- `(owner_type, owner_id, artifact_name)` 唯一
- `artifact_type` 建议建立索引
- `parent_artifact_id` 建议建立索引
- `status` 建议建立索引

---

## 11.3 sync_checkpoints 同步检查点表

### 表作用

用于保存平台与 ClearML 之间的同步进度和同步状态。

该表的职责是：

- 记录某类同步任务的最近游标
- 记录最后同步时间
- 记录同步结果
- 记录失败原因
- 支持补偿同步和回放同步

### 字段设计

| 字段名 | 类型 | 是否必填 | 中文名称 | 字段说明 |
|---|---|---:|---|---|
| `id` | INTEGER | 是 | 主键 ID | 平台内部主键，自增标识。 |
| `sync_domain` | VARCHAR(64) | 是 | 同步领域 | 同步对象类别，如 `tasks.training`、`tasks.export`、`tasks.quantization`。 |
| `last_cursor` | VARCHAR(255) | 否 | 最后游标 | 最近一次同步到的位置标记，可存时间戳或分页游标。 |
| `last_sync_at` | DATETIME | 否 | 最后同步时间 | 最近一次执行同步的时间。 |
| `last_sync_status` | VARCHAR(32) | 否 | 最后同步状态 | 最近一次同步结果，如 `success/failed/running`。 |
| `last_sync_error` | TEXT | 否 | 最后同步错误 | 最近一次同步失败的错误信息。 |
| `sync_version` | INTEGER | 是 | 同步版本号 | 当前同步版本号，用于控制并发和重复执行。 |
| `created_at` | DATETIME | 是 | 创建时间 | 本地记录创建时间。 |
| `updated_at` | DATETIME | 是 | 更新时间 | 本地记录更新时间。 |

### 约束建议

- `sync_domain` 唯一

---

## 11.4 job_runs 调度作业运行表

### 表作用

用于记录调度器执行的每一次后台作业运行情况。

该表的职责是：

- 记录 Cron 作业执行历史
- 支持故障排查
- 支持后台作业运行可视化
- 支持统计失败率和运行时长

### 字段设计

| 字段名 | 类型 | 是否必填 | 中文名称 | 字段说明 |
|---|---|---:|---|---|
| `id` | INTEGER | 是 | 主键 ID | 平台内部主键，自增标识。 |
| `job_name` | VARCHAR(128) | 是 | 作业名称 | 调度作业名称，如 `sync_running_training_tasks`。 |
| `trigger_time` | DATETIME | 否 | 触发时间 | 计划调度触发时间。 |
| `started_at` | DATETIME | 否 | 开始时间 | 实际开始执行时间。 |
| `finished_at` | DATETIME | 否 | 结束时间 | 实际执行结束时间。 |
| `status` | VARCHAR(32) | 是 | 执行状态 | 作业执行结果，如 `running/succeeded/failed`。 |
| `summary_json` | TEXT | 否 | 执行摘要 JSON | 作业执行摘要，如同步条数、成功数、失败数。 |
| `error_message` | TEXT | 否 | 错误信息 | 作业失败时的错误信息。 |
| `created_at` | DATETIME | 是 | 创建时间 | 本地记录创建时间。 |
| `updated_at` | DATETIME | 是 | 更新时间 | 本地记录更新时间。 |

### 约束建议

- `job_name` 建议建立索引
- `status` 建议建立索引
- `started_at` 建议建立索引

---

## 11.5 model_families 模型族表

### 表作用

该表为后续模型仓库阶段预留，用于管理业务视角下的模型族主档。

示例：

- 车辆颜色分类器
- 车牌检测器
- OCR 识别器

模型族表示“同一类业务模型资产”的上层归类，是模型仓库的第一层，不等同于某次训练任务、某个模型版本或某个具体模型文件。

### 字段设计

| 字段名 | 类型 | 是否必填 | 中文名称 | 字段说明 |
|---|---|---:|---|---|
| `id` | INTEGER | 是 | 主键 ID | 平台内部主键，自增标识。 |
| `code` | VARCHAR(128) | 是 | 模型编码 | 模型族的唯一编码。 |
| `name` | VARCHAR(255) | 是 | 模型名称 | 模型族名称。 |
| `model_type` | VARCHAR(64) | 否 | 模型类型 | 分类、检测、OCR 等。 |
| `description` | TEXT | 否 | 模型描述 | 模型说明。 |
| `training_template_id` | INTEGER | 否 | 训练模板 ID | 关联 `parameter_templates.id`，用于训练发起时回填默认训练配置。 |
| `export_template_id` | INTEGER | 否 | 导出模板 ID | 关联 `parameter_templates.id`，用于导出 ONNX 或其他格式时回填默认导出参数。 |
| `quantization_template_id` | INTEGER | 否 | 量化模板 ID | 关联 `parameter_templates.id`，用于量化任务回填默认量化参数。 |
| `prediction_template_id` | INTEGER | 否 | 预测模板 ID | 关联 `parameter_templates.id`，用于调试预测回填默认预测参数。 |
| `status` | VARCHAR(32) | 是 | 状态 | 建议取值为 `enabled/disabled`。 |
| `created_by` | VARCHAR(128) | 否 | 创建人 | 预留给后续认证系统，用于记录创建该模型族的用户标识。 |
| `updated_by` | VARCHAR(128) | 否 | 更新人 | 预留给后续认证系统，用于记录最后更新该模型族的用户标识。 |
| `created_at` | DATETIME | 是 | 创建时间 | 本地记录创建时间。 |
| `updated_at` | DATETIME | 是 | 更新时间 | 本地记录更新时间。 |

### 约束建议

- `code` 唯一
- `name` 建议建立索引

---

## 11.6 model_versions 模型版本表

### 表作用

该表为后续模型仓库阶段预留，用于保存正式模型版本信息。

### 字段设计

| 字段名 | 类型 | 是否必填 | 中文名称 | 字段说明 |
|---|---|---:|---|---|
| `id` | INTEGER | 是 | 主键 ID | 平台内部主键，自增标识。 |
| `model_family_id` | INTEGER | 是 | 模型族 ID | 关联 `model_families.id`。 |
| `version` | VARCHAR(64) | 是 | 版本号 | 模型族内唯一版本号，如 `v1.0`。 |
| `version_name` | VARCHAR(255) | 否 | 版本名称 | 版本的展示名称。 |
| `status` | VARCHAR(32) | 是 | 版本状态 | 建议取值为 `draft/testing/production/archived`。 |
| `source_task_id` | INTEGER | 否 | 来源任务 ID | 对应产生该版本的来源任务，不限定只能是训练任务。 |
| `description` | TEXT | 否 | 版本描述 | 版本说明。 |
| `registered_by` | VARCHAR(128) | 否 | 注册人 | 谁执行了版本注册。 |
| `registered_at` | DATETIME | 否 | 注册时间 | 版本注册时间。 |
| `created_at` | DATETIME | 是 | 创建时间 | 本地记录创建时间。 |
| `updated_at` | DATETIME | 是 | 更新时间 | 本地记录更新时间。 |

### 约束建议

- `(model_family_id, version)` 唯一

---

## 11.7 model_files 模型文件表

### 表作用

该表为后续模型仓库阶段预留，用于保存模型版本下的正式文件资产。

### 字段设计

| 字段名 | 类型 | 是否必填 | 中文名称 | 字段说明 |
|---|---|---:|---|---|
| `id` | INTEGER | 是 | 主键 ID | 平台内部主键，自增标识。 |
| `model_version_id` | INTEGER | 否 | 模型版本 ID | 关联 `model_versions.id`。 |
| `source_task_id` | INTEGER | 否 | 来源任务 ID | 来源训练任务或转换任务的 ID。 |
| `parent_model_file_id` | INTEGER | 否 | 父模型文件 ID | 文件血缘关系，如 ONNX 来自 PT。 |
| `file_name` | VARCHAR(255) | 是 | 文件名称 | 如 `best.pt`、`best.onnx`。 |
| `file_type` | VARCHAR(64) | 是 | 文件类型 | 如 `pt`、`onnx`、`om`、`rknn`、`nb`。 |
| `storage_uri` | VARCHAR(512) | 否 | 存储地址 | 文件存储路径。 |
| `framework` | VARCHAR(64) | 否 | 框架类型 | 如 `pytorch`、`onnx`。 |
| `device_type_id` | INTEGER | 否 | 设备类型 ID | 关联设备类型表。 |
| `status` | VARCHAR(32) | 是 | 文件状态 | 建议取值为 `pending/ready/failed/deleted`。 |
| `metadata_json` | TEXT | 否 | 元数据 JSON | 文件的补充元信息。 |
| `created_at` | DATETIME | 是 | 创建时间 | 本地记录创建时间。 |
| `updated_at` | DATETIME | 是 | 更新时间 | 本地记录更新时间。 |

---

## 11.8 parameter_templates 参数模板表

### 表作用

该表用于统一管理训练、导出、量化、预测等参数模板。

设计该表的原因：

- 训练、导出、量化、预测的参数差异大，不适合为每类模板单独设计一套固定字段表。
- 运行环境、执行目录、入口脚本、命令模板和默认参数都需要配置化管理。
- 后续不同算法栈的参数集合变化频繁，使用 JSON 更利于扩展。
- 前端需要根据模板自动回填默认值，后端需要根据模板渲染最终执行参数。

该表不是简单保存裸 CLI 参数，而是保存“模板元数据 + 参数定义 + 默认值 + 执行配置”。

### 字段设计

| 字段名 | 类型 | 是否必填 | 中文名称 | 字段说明 |
|---|---|---:|---|---|
| `id` | INTEGER | 是 | 主键 ID | 平台内部主键，自增标识。 |
| `code` | VARCHAR(128) | 是 | 模板编码 | 参数模板的唯一编码。 |
| `name` | VARCHAR(255) | 是 | 模板名称 | 模板展示名称。 |
| `template_type` | VARCHAR(32) | 是 | 模板类型 | 模板类别，建议取值为 `training/export/quantization/prediction`。 |
| `engine_type` | VARCHAR(64) | 否 | 引擎类型 | 模板对应的技术栈，如 `yolo`、`convnext`、`unet`。 |
| `runtime_type` | VARCHAR(32) | 否 | 运行时类型 | 运行环境类型，如 `venv`、`conda`、`docker`。 |
| `runtime_config_json` | TEXT | 否 | 运行环境配置 JSON | 记录 Python 版本、环境名、镜像名、GPU 要求等运行环境配置。 |
| `execution_config_json` | TEXT | 否 | 执行配置 JSON | 记录仓库地址、分支、执行目录、入口脚本、命令模板、队列等执行配置。 |
| `parameter_schema_json` | TEXT | 否 | 参数定义 JSON | 定义参数键、中文名、类型、必填性、默认值、是否可编辑、CLI 映射等。 |
| `default_values_json` | TEXT | 否 | 默认参数值 JSON | 模板默认参数值，用于前端表单回填和后端参数合并。 |
| `artifact_rules_json` | TEXT | 否 | 产物规则 JSON | 描述任务预期产物名称、类型、关键文件规则等。 |
| `status` | VARCHAR(32) | 是 | 状态 | 建议取值为 `enabled/disabled`。 |
| `description` | TEXT | 否 | 模板描述 | 模板说明。 |
| `created_by` | VARCHAR(128) | 否 | 创建人 | 预留给后续认证系统，用于记录创建该模板的用户标识。 |
| `updated_by` | VARCHAR(128) | 否 | 更新人 | 预留给后续认证系统，用于记录最后更新该模板的用户标识。 |
| `created_at` | DATETIME | 是 | 创建时间 | 本地记录创建时间。 |
| `updated_at` | DATETIME | 是 | 更新时间 | 本地记录更新时间。 |

### 字段设计说明

#### 1. `parameter_schema_json`

用于定义参数的业务语义和展示规则，建议按如下结构组织：

```json
[
  {
    "key": "imgsz",
    "label": "输入尺寸",
    "type": "int",
    "required": true,
    "default": 640,
    "editable": true,
    "cli_flag": "--imgsz"
  }
]
```

#### 2. `default_values_json`

用于保存模板默认值，建议按如下结构组织：

```json
{
  "imgsz": 640,
  "batch": 16,
  "data": "/mnt/sd1/data.yaml"
}
```

#### 3. `execution_config_json`

用于保存执行入口相关信息，建议包含：

- `repo_url`
- `repo_branch`
- `work_dir`
- `entrypoint`
- `command_template`
- `default_queue`

#### 4. `runtime_config_json`

用于保存运行环境相关信息，建议包含：

- `python_version`
- `venv_path`
- `conda_env`
- `docker_image`
- `device_requirements`

### 约束建议

- `code` 唯一
- `template_type` 建议建立索引
- `engine_type` 建议建立索引
- `status` 建议建立索引

---

## 12. SQLite 使用约束与扩展策略

### 12.1 一期使用 SQLite 的原因

- 部署简单
- 不需要额外数据库服务
- 适合一期 MVP 和内网管理平台场景

### 12.2 使用注意事项

1. SQLite 适合中低并发后台系统，不适合作为高并发核心数据库。
2. 数据库写操作应尽量保持短事务。
3. 调度作业应控制并发，避免多个任务同时大量写库。
4. 业务逻辑不要依赖 SQLite 特有能力，降低迁移成本。

### 12.3 扩展策略

后续迁移 PostgreSQL 时：

- 保留 SQLAlchemy ORM 模型
- 调整数据库连接配置
- 重新执行 Alembic 迁移
- 仓储接口与应用服务层不需要大改

---

## 13. ClearML 集成设计

### 13.1 集成原则

1. ClearML 对接能力统一收敛到 `infrastructure/clearml`。
2. 业务层不直接调用 ClearML SDK。
3. 平台内部使用 DTO 或 Mapper 转换 ClearML 原始对象。

### 13.2 适配层建议

建议拆分为以下组件：

- `TaskQueryClient`
  - 查询任务列表
  - 查询任务详情
  - 查询产物信息

- `TaskSubmitClient`
  - 创建导出 ONNX 任务
  - 指定队列
  - 注入执行参数
  - 建立来源任务关系

- `TaskMapper`
  - 将 ClearML 原始对象映射为平台内部 DTO

- `ClearMLAdapter`
  - 对外提供统一调用入口

### 13.3 ClearML 配置要求

ClearML 相关配置必须放在配置文件中，至少包括：

- `api_server`
- `web_server`
- `files_server`
- `access_key`
- `secret_key`
- `verify_ssl`
- `request_timeout_seconds`
- `default_project`
- `queue` 映射

---

## 13.4 参数模板与执行渲染机制

### 设计目标

参数模板体系需要同时满足：

- 前端可根据模板自动回填默认值
- 后端可根据模板校验用户输入
- 后端可将业务参数渲染为最终执行参数
- 不把底层 CLI Flag 直接暴露为唯一领域模型

### 推荐机制

采用如下处理流程：

```text
参数模板定义
  + 默认参数值
  + 用户提交覆盖值
    ↓
参数合并
    ↓
参数校验
    ↓
执行渲染
    ↓
下发 ClearML 任务
```

### 设计要求

1. 模板表保存业务键和 CLI 映射，而不是只保存裸 CLI 参数。
2. 最终渲染结果可以是 `{"--imgsz": 640}` 形式，但模板主存储不建议直接采用这种低语义结构。
3. 历史任务必须保存当次执行参数快照，不能只保存模板 ID。

### 与模型族的关系

模型族可分别绑定：

- 一个训练模板
- 一个导出模板
- 一个量化模板
- 一个预测模板

用户选择模型族后，平台可自动带出对应模板的：

- 默认训练参数
- 默认运行环境
- 默认执行目录
- 默认命令模板
- 默认队列

---

## 14. 同步与幂等设计

### 14.1 同步模式

采用：

```text
ClearML -> 定时同步 -> 本地 SQLite -> 前端查询
```

### 14.2 同步分类

建议至少有以下同步作业：

- 运行中训练类任务同步
- 已完成训练类任务补充同步
- 运行中导出/转换类任务同步
- 失败任务补偿同步

### 14.3 幂等策略

1. 以 `clearml_task_id` 作为外部幂等主键。
2. 同步逻辑采用“存在则更新，不存在则插入”。
3. 已终态任务不允许被低优先级状态覆盖。

补充约束：

- 当 `task_source = clearml` 时，以 `clearml_task_id` 作为外部幂等键。
- 当 `task_source != clearml` 时，幂等应由平台内部业务键控制，不依赖 ClearML 字段。

### 14.4 状态优先级

建议状态优先级如下：

```text
queued < running < succeeded
queued < running < failed
queued < cancelled
running < cancelled
```

### 14.5 同步可靠性要求

- 幂等：重复同步不产生重复记录
- 可补偿：失败后支持重试
- 可追踪：记录最后同步时间、状态、错误
- 可恢复：ClearML 短时不可用时不影响平台已有数据查询
- 可回放：支持按任务 ID 或时间窗口重同步

---

## 15. 调度器设计

### 15.1 选型

内嵌调度器采用 `APScheduler`。

### 15.2 调度原则

1. 调度器只负责触发，不直接写业务逻辑。
2. 每个调度作业统一调用应用服务层。
3. 作业执行结果需要落库到 `job_runs`。
4. 一期架构下调度器只能在单实例进程中启用。

### 15.3 作业配置方式

支持按 Cron 表达式配置，例如：

```yaml
scheduler:
  jobs:
    sync_running_training_tasks:
      cron: "0 */1 * * *"
```

后续也可扩展：

```yaml
every_seconds: 300
```

### 15.4 推荐一期作业

- `sync_running_training_tasks`
- `sync_finished_training_tasks`
- `sync_running_export_tasks`
- `retry_failed_sync`

### 15.5 作业运行要求

每个作业执行时都应：

- 记录开始时间
- 记录结束时间
- 记录执行摘要
- 捕获异常并记录错误
- 控制最大并发数
- 避免在多实例部署下重复注册与重复执行

---

## 16. API 设计建议

### 16.1 一期 API 主题

建议一期先提供以下接口：

#### 任务接口

- `GET /tasks`
  - 查询任务列表
- `GET /tasks/{id}`
  - 查询任务详情
- `POST /tasks/{id}/export-onnx`
  - 基于某个训练类任务发起 ONNX 导出

#### 系统接口

- `GET /health`
  - 健康检查
- `GET /system/config`
  - 查看系统运行配置摘要
- `GET /system/jobs`
  - 查看调度作业运行情况

### 16.2 API 路径要求

必须支持：

- `host` 配置
- `port` 配置
- `root_path` 配置

例如：

- 服务监听：`0.0.0.0:18087`
- API 根路径：`/api`
- 最终接口地址：`/api/tasks`

---

## 17. 日志与可观测性设计

### 17.1 日志要求

日志体系必须支持：

- 控制台输出
- 文件输出
- 文件轮转
- JSON 结构化日志
- Access Log
- 调度作业日志

### 17.2 推荐日志字段

建议统一输出以下字段：

- `timestamp`
- `level`
- `logger`
- `message`
- `request_id`
- `trace_id`
- `job_name`
- `task_id`
- `clearml_task_id`
- `module`
- `exception`

### 17.3 日志配置项

日志配置建议包括：

- `level`
- `format`
- `file_enabled`
- `file_path`
- `rotate.when`
- `rotate.backup_count`
- `access_log`
- `sql_log`

### 17.4 观测性建议

一期即应具备：

- 请求级 `request_id`
- 调度级 `job_name`
- ClearML 任务级 `clearml_task_id`
- 预留用户级 `user_id`
- 预留用户级 `username`

这样能将前端请求、后台调度、ClearML 任务串联起来。

### 17.5 IAM 扩展预留原则

当前阶段不详细设计 IAM，但为了避免后续重构，建议遵循以下约束：

1. API 层预留统一认证依赖入口，例如：
   - `get_current_user()`
   - `require_permission()`

2. 业务服务层不要写死具体角色名称，例如“只有管理员可执行”。
   - 应预留权限点常量位，例如：
     - `task:create`
     - `task:export_onnx`
     - `model_version:register`

3. 关键业务对象后续应支持记录操作人或归属人。
   - 如 `created_by`
   - `updated_by`
   - `owner_id`

4. 操作日志与安全日志应作为独立关注点处理，不散落在业务逻辑中。

5. 当前阶段可默认鉴权关闭或空实现放行，但路由结构和服务调用链要保留接入点。

---

## 18. 一期 MVP 落地范围

### 18.1 一期建设目标

一期聚焦最小闭环：

```text
平台展示训练类任务
  ↓
在任务详情发起导出 ONNX
  ↓
平台创建 ClearML 导出任务
  ↓
Agent 执行任务
  ↓
平台同步导出结果
  ↓
平台展示 ONNX 文件信息
```

### 18.2 一期必做内容

- 建立统一任务主表模型
- 建立任务产物表
- 建立 ClearML 同步服务
- 建立内嵌调度器
- 建立 ONNX 导出接口
- 建立导出任务状态同步
- 展示导出成功产物和失败原因

### 18.3 一期暂不纳入

- 模型仓库完整能力
- 正式模型版本注册
- ONNX 到海思 / 联咏 / RKNN 转换
- 离线评测体系
- 全局模型预测入口
- 审批、发布、回滚

---

## 19. 后续演进路线

### 19.1 第二阶段

- 建立模型族、模型版本、模型文件体系
- 增加“注册为模型版本”
- 打通模型仓库详情页

### 19.2 第三阶段

- 增加 ONNX -> 海思 / 联咏 / RKNN 转换
- 建立文件血缘
- 建立转换任务链路视图

### 19.3 第四阶段

- 增加调试预测与离线评测
- 接入边缘推理服务
- 回传评测结果到平台与 ClearML

### 19.4 第五阶段

- 将调度器拆成独立进程
- 将 SQLite 迁移为 PostgreSQL
- 根据需要引入 Redis 或消息队列
- 根据多系统复用需求决定是否拆分独立认证与权限中心

---

## 20. 架构结论

本方案采用：

```text
Python 3.12 + .venv
FastAPI + SQLAlchemy + APScheduler + SQLite
模块化单体 + 内嵌调度 + 共享服务层直调
```

该方案的特点是：

- 一期实现成本低，能快速落地 MVP
- 配置外置充分，端口、根路径、Cron、ClearML、日志均可配置
- 模块边界清晰，训练、转换、同步、系统能力分离
- 数据模型独立于 ClearML，便于形成平台主数据
- 后续可平滑扩展到模型仓库、评测、推理和独立调度进程

因此，该方案适合作为当前自研平台 MLOps 后端系统的一期基础架构。
