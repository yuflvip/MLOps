# 自研 MLOps 与 ClearML 集成需求整理

```
ClearML api 官方文档：https://clear.ml/docs/latest/docs/references/api/#open-source-server-api-services
```

## 1. 背景

当前已完成的基础能力：

- 已搭建 ClearML。
- 可以在 ClearML 下发任务。
- Agent 可以自动领取任务、执行任务并上报状态与结果。
- ClearML 页面已经可以看到任务执行结果。

在此基础上，下一步目标不是继续堆叠 ClearML 页面能力，而是建设一个以业务人员为主入口的自研 MLOps 管理平台，并把 ClearML 作为底层实验追踪与任务执行引擎。

---

## 2. 建设目标

建设一个自研 MLOps 管理平台，满足以下目标：

- 提供中文化、可定制的业务入口。
- 统一训练、导出、转换、评测、预测、模型版本管理入口。
- 让大部分操作都从自研平台发起。
- 使用 ClearML 承载任务留痕、日志、指标、产物和队列调度。
- 支持 YOLO 训练产物向 ONNX、海思、联咏、RKNN 等格式演进。
- 最终形成可管理的模型资产，而不是只保存实验记录。

---

## 3. 术语定义

为避免后续讨论混淆，本文统一使用以下术语：

- 算法模型：面向业务的模型大类，例如“车辆颜色分类器”“车牌检测器”。
- 模型版本：算法模型下的正式资产版本，例如 `v1.0`、`v2.0`。
- 模型文件：某个模型版本下的具体文件，例如 `best.pt`、`best.onnx`、`best.om`。
- 训练任务：训练过程本身，对应一次训练执行记录。
- 转换任务：模型格式转换过程，例如 `PT -> ONNX`、`ONNX -> 海思`。
- 评测任务：离线指标验证过程，例如数据集评测、性能评测。
- 调试预测：人工发起的单图/单视频验证，用于快速确认模型效果。
- 在线推理：真实业务链路中的实时推理服务，不等同于调试预测。
- 边缘推理服务：负责 RKNN / 海思 / 联咏等设备模型加载和实时推理的自研服务。

---

## 4. 范围边界

### 4.1 一期范围

一期聚焦最小闭环，只做以下内容：

- 建立自研 MLOps 平台的基础业务数据模型。
- 建立 ClearML 与自研数据库之间的同步机制。
- 建立训练任务列表和训练任务详情页的最小展示能力。
- 支持在平台内基于 YAML 训练模板创建训练任务，并下发到 ClearML 队列。
- 在训练任务详情页发起 `PT -> ONNX` 导出。
- 创建 ClearML 导出任务并跟踪状态。
- 导出成功后在平台展示 ONNX 文件和任务结果。

补充约定：

- 一期采用统一任务表方案，以 `tasks` 和 `task_artifacts` 作为核心主数据模型。
- `PT -> ONNX` 导出任务基于已有训练任务派生 `child task`，通过 `parent_task_id` 关联来源训练任务。
- 页面创建训练任务时需要可见 ClearML 队列和 Agent 在线状态；当目标队列当前没有在线 Agent 时，平台允许提交并给出告警提示。

### 4.2 二期及以后范围

以下内容纳入后续阶段，不作为一期上线必需项：

- 模型仓库完整能力
- 注册为模型版本
- ONNX -> 海思 / 联咏 / RKNN 转换
- 评测记录与性能指标沉淀
- 全局模型预测菜单
- 审批、发布、回滚
- RTSP / 视频流预测
- 多模型对比

### 4.3 明确不在当前文档解决的问题

以下内容本次只定义方向，不在本文档中展开实施细节：

- 边缘设备侧 SDK 封装细节
- 多租户隔离方案
- 权限系统实现细节
- 对象存储选型
- 生产环境部署拓扑

---

## 5. 总体架构结论

推荐采用混合架构：

```text
自研 MLOps 平台
  负责：入口、权限、流程、业务模型、资产管理、结果展示

ClearML
  负责：Task、Agent、Queue、日志、指标、Artifacts、模型文件、实验追踪

边缘推理服务
  负责：RKNN / 海思 / 联咏等设备侧真实推理
```

不建议：

- 直接把 ClearML 当最终业务平台使用。
- 在自研平台后端直接用 `subprocess` 长时间执行导出、转换、评测任务。
- 把生产实时推理主链路接到 ClearML。

说明：

- 本章是总体设计结论，不等同于一期全部实现范围。
- 一期先落地“自研平台 + ClearML 同步 + PT 导出 ONNX 闭环”。

---

## 6. 平台边界划分

### 6.1 自研 MLOps 平台负责

- 中文界面
- 项目/算法任务管理
- 训练入口
- ONNX / RKNN / 海思 / 联咏转换入口
- 模型仓库主入口
- 模型版本管理
- 模型审批、发布、回滚
- 列表、筛选、权限控制
- 业务状态管理
- 结果汇总展示

### 6.2 ClearML 负责

- 训练 Task 记录
- 导出 Task 记录
- 转换 Task 记录
- 评测 Task 记录
- 任务日志
- 指标曲线
- Artifacts
- OutputModel / 模型注册
- 队列调度
- Agent 执行

### 6.3 边缘推理服务负责

- 加载 RKNN / 海思 / 联咏模型
- 调用 NPU SDK
- 图像预处理与 YOLO 后处理
- HTTP / REST 推理接口
- 在线推理

---

## 7. 数据归属与同步策略

推荐方案：

```text
ClearML
  ↓ 定时/事件同步
自研 MLOps 数据库
  ↓
前端展示
```

### 7.1 自研数据库保存

- 业务字段
- 展示字段
- 状态字段
- 模型类型
- 版本关系
- 审批状态
- 发布状态
- ClearML task_id / model_id / project_id

建议同步后的任务字段至少包括：

```text
task_id
task_name
task_type
model_type
status
created_time
started_time
completed_time
dataset_version
best_metric
owner
clearml_task_id
clearml_project_id
source_task_id
error_message
```

### 7.2 ClearML 保存

- 完整日志
- 训练参数
- Loss / 指标曲线
- Artifacts
- 模型文件
- 原始实验记录

### 7.3 页面读取策略

- 列表页、搜索页、筛选页：读自研数据库
- 详情页基础信息：读自研数据库
- 详情页实时日志、曲线、Artifacts：实时查询 ClearML 补充
- 训练任务创建页的模板、队列与 Agent 在线状态：实时查询配置和 ClearML 补充，不依赖本地同步表

### 7.4 同步频率建议

```text
运行中任务：10~30 秒同步一次
已完成任务：几分钟同步一次
失败任务：优先同步错误信息
已归档任务：低频或不再同步
```

### 7.5 同步可靠性要求

同步服务除轮询外，还应满足以下要求：

- 幂等：同一个 ClearML Task 多次同步不会产生重复数据。
- 可补偿：某次同步失败后，后续任务可重试并补齐缺失数据。
- 可追踪：记录最后同步时间、最后同步状态、最后错误信息。
- 可恢复：ClearML 短时不可用时，不影响自研平台已有数据查询。
- 可回放：支持按任务 ID 或时间窗口重新同步。

建议在自研数据库中为同步对象增加以下辅助字段：

```text
last_sync_time
last_sync_status
last_sync_error
sync_version
```

---

## 8. 核心业务对象设计

推荐先定义自己的业务数据模型，而不是直接暴露 ClearML 原始对象。

说明：

- 本章中的 `algorithm_model`、`model_version`、`training_task`、`conversion_task`、`model_file` 等名称用于表达业务概念边界。
- 一期数据库落地已确认采用统一任务表方案，即以 `tasks` 和 `task_artifacts` 为核心主数据模型。
- 因此本章不再作为一期物理落库分表方案的直接依据，若与统一表方案冲突，以架构设计文档中的一期确认结论为准。

### 8.1 首批核心表

```text
algorithm_model      算法模型
model_version        模型版本
training_task        训练任务
conversion_task      转换任务
evaluation_task      评测任务
model_file           模型文件
device_type          设备类型
```

### 8.2 核心关系示例

```text
车辆颜色分类器
  └── v1.0
       ├── best.pt
       ├── best.onnx
       ├── best_hisi3403.om
       └── best_692.nb
```

### 8.3 主关系定义

- 一个 `algorithm_model` 可以有多个 `model_version`。
- 一个 `model_version` 必须归属一个 `algorithm_model`。
- 一个 `model_version` 可以绑定多个 `model_file`。
- 一个 `training_task` 可以产生多个候选文件，但默认只允许注册到一个正式 `model_version`。
- 一个 `conversion_task` 必须有一个 `source_model_file`，并产生一个 `output_model_file`。
- 一个 `evaluation_task` 可以针对 `model_version` 或 `model_file` 执行，但落库时必须明确目标对象。

### 8.4 建议关键字段

`algorithm_model`

```text
id
code                  唯一编码
name                  名称
model_type            分类/检测/OCR 等
description
status                enabled/disabled
```

`model_version`

```text
id
algorithm_model_id
version               版本号，算法模型内唯一
version_name
status                draft/testing/production/archived
source_training_task_id
description
registered_by
registered_at
```

`model_file`

```text
id
model_version_id      可为空；未注册版本前允许为空
source_task_id
parent_model_file_id  文件血缘，例如 onnx 的父文件是 pt
file_name
file_type             pt/onnx/om/nb/rknn/txt/json
storage_uri
framework
device_type_id
status                pending/ready/failed/deleted
```

`training_task`

```text
id
clearml_task_id       唯一
clearml_project_id
task_name
status                queued/running/succeeded/failed/cancelled
dataset_version
owner
best_metric
started_time
completed_time
error_message
```

`conversion_task`

```text
id
clearml_task_id       唯一
source_model_file_id
output_model_file_id
target_format
target_device
params_json
status                queued/running/succeeded/failed/cancelled
started_time
completed_time
error_message
```

`evaluation_task`

```text
id
clearml_task_id       唯一
target_type           model_version/model_file
target_id
eval_type             accuracy/performance/regression
metrics_json
status                queued/running/succeeded/failed/cancelled
```

### 8.5 建议唯一约束

- `algorithm_model.code` 全局唯一
- `model_version (algorithm_model_id, version)` 唯一
- `training_task.clearml_task_id` 唯一
- `conversion_task.clearml_task_id` 唯一
- `evaluation_task.clearml_task_id` 唯一

### 8.6 状态机建议

任务类对象统一采用：

```text
queued -> running -> succeeded
queued -> running -> failed
queued -> cancelled
running -> cancelled
```

模型版本统一采用：

```text
draft -> testing -> production -> archived
draft -> archived
testing -> archived
production -> archived
```

模型文件统一采用：

```text
pending -> ready
pending -> failed
ready -> deleted
failed -> deleted
```

---

## 9. 模型仓库设计

模型仓库不应直接展示“每次训练的产物”，而应采用三级结构：

```text
算法模型
  ↓
模型版本
  ↓
模型文件
```

### 9.1 第一层：算法模型

示例：

```text
模型仓库
├── 车辆颜色分类器
├── 6分类检测器
├── 车牌号码检测器
├── 车牌 OCR 识别器
├── 人脸检测器
└── 安全帽检测器
```

### 9.2 第二层：模型版本

示例：

```text
车辆颜色分类器
├── v1.0
├── v1.1
├── v1.2
└── v2.0
```

建议版本维度展示：

| 版本 | 指标 | 数据集 | 状态 |
|---|---|---|---|
| v1.0 | 91.2% | dataset_v1 | 已归档 |
| v1.1 | 92.8% | dataset_v2 | 已归档 |
| v1.2 | 93.5% | dataset_v3 | 生产 |
| v2.0 | 94.2% | dataset_v4 | 测试 |

### 9.3 第三层：模型文件

示例：

```text
车辆颜色分类器
 └── v2.0
      ├── best.pt
      ├── best.onnx
      ├── best.om
      ├── best_692.nb
      ├── labels.txt
      └── quant_config.json
```

### 9.4 版本详情页组成

版本详情页建议由以下模块组成：

- 基础信息：算法模型、版本号、状态、描述、来源训练任务
- 模型文件：当前版本下所有文件
- 转换记录：该版本下相关 `conversion_task` 的聚合视图
- 评测记录：该版本或该版本文件相关 `evaluation_task` 的聚合视图
- 发布记录：版本状态变更与发布动作日志

说明：

- “训练记录 / 转换记录 / 评测记录 / 发布记录”在实现上建议都是任务或事件对象的聚合视图，不建议再造一套并行主数据。

---

## 10. 训练任务与模型仓库的关系

训练完成后，不建议自动进入模型仓库。

### 10.1 推荐流程

训练完成后先进入：

```text
训练任务
```

任务详情中展示：

- 状态
- 关键指标
- best.pt
- best.onnx（如果已导出）

然后提供按钮：

```text
[注册为模型版本]
```

### 10.2 注册为模型版本

只有用户确认后，训练结果才进入模型仓库。

注册时填写：

```text
所属算法模型
版本号
版本描述
状态：testing / production / archived
```

### 10.3 注册规则建议

- 只有具备对应权限的用户可以执行“注册为模型版本”。
- 同一个训练任务默认只允许注册一个正式模型版本；如需再次注册，应走复制/派生流程。
- `version` 在同一个 `algorithm_model` 内必须唯一。
- 注册时必须明确一个主模型文件，默认主文件为 `best.pt` 或指定产物。
- 注册成功后生成 `model_version`，并把相关 `model_file` 绑定到该版本。
- 注册失败时不得产生半成品版本记录；应整体回滚。

### 10.4 这样设计的原因

- 训练任务大多是实验，不一定值得沉淀为正式模型资产。
- 避免模型仓库被大量无效实验污染。
- 让“实验记录”和“模型资产管理”明确分层。

---

## 11. 菜单与入口设计

### 11.1 总体原则

入口应尽量集中在模型仓库 / 模型详情页，不建议拆成多个零散菜单。

推荐结构：

```text
模型仓库
 └── 模型详情
      ├── 基础信息
      ├── 模型文件
      ├── 转换记录
      ├── 评测记录
      └── 发布记录
```

### 11.2 PT 转 ONNX 入口

放在：

```text
模型详情 → 模型文件 → best.pt → 导出 ONNX
```

原因：

- ONNX 是 PT 派生物，用户心智最自然。

### 11.3 ONNX 转海思 / 联咏 / RKNN 入口

放在：

```text
模型详情 → 模型文件 → best.onnx → 转换
```

按钮示例：

```text
[转海思模型]
[转联咏692模型]
[转联咏530模型]
[转 RKNN 模型]
```

### 11.4 调试预测 / 评测入口

放在对应模型文件旁边：

```text
best.onnx       [调试预测] [离线评测]
best_hisi.om    [调试预测] [离线评测]
best_692.nb     [调试预测] [离线评测]
```

### 11.5 全局“模型预测”菜单

建议单独保留一个“模型预测”菜单，方便从全局发起调试预测，但模型来源仍然只来自模型仓库。

两个入口并存：

1. 模型详情页中的“上下文入口”：用户已定位到具体模型版本。
2. 左侧“模型预测”菜单中的“全局入口”：用户先选择模型与版本，再发起调试预测。

预测菜单的典型流程：

```text
模型预测
  ↓
选择模型
  ↓
选择版本
  ↓
上传图片 / 视频 / RTSP
  ↓
开始调试预测
```

---

## 12. 任务执行方式设计

不要按功能名决定任务归属，而要按以下标准判断：

- 是否耗时
- 是否需要留痕
- 是否依赖特定环境
- 是否需要排队调度

### 12.1 推荐执行方式

| 功能 | 推荐方式 | 说明 |
|---|---|---|
| PT -> ONNX | ClearML Task | 需要记录来源训练、参数、产物 |
| PT / ONNX 调试预测 | 可直接平台 API；批量评测走 ClearML Task | 调试轻量，批量需留痕 |
| ONNX -> 海思3403 | ClearML Task | 参数多，需要留痕 |
| ONNX -> 联咏692/530 | ClearML Task + Docker Queue | 环境依赖强，适合容器隔离 |
| ONNX / 海思 / 联咏离线评测 | ClearML Task | 需要保存 mAP / FPS / Latency / 样例图 |
| 在线推理 | 自研 REST API | ClearML 不适合在线实时推理 |

### 12.2 队列建议

按环境拆分队列，例如：

```text
queue_train_gpu
queue_export_onnx
queue_convert_hisi
queue_convert_novatek_692
queue_convert_novatek_530
queue_evaluation
```

说明：

- 本章为推荐实现方案，不代表一期必须一次性全部建设。

---

## 13. 边缘推理服务设计

对于导出的 ONNX、RKNN、海思、联咏等模型，推荐采用：

```text
自研 REST API 做真实边缘推理
ClearML 做模型管理、版本追踪、评测记录
```

原因：

- 边缘设备推理通常依赖特定 NPU Runtime / SDK。
- 需要自定义模型加载、前处理、后处理和设备调用。
- ClearML 不适合作为实时推理主链路。

适合的链路：

```text
YOLO 训练 Task
   ↓
导出 ONNX Task
   ↓
转换 RKNN / 海思 / 联咏模型 Task
   ↓
边缘推理服务
   ↓
评测结果 / 样例图 / 指标回传 ClearML
```

---

## 14. 结果回传 ClearML 的原则

结论：按场景区分，不要把所有在线推理结果都回传。

### 14.1 建议回传的内容

- 训练 Task
- ONNX 导出 Task
- RKNN / 海思 / 联咏转换 Task
- mAP 评测结果
- FPS
- Latency
- 少量预测样例图（例如 10~100 张）

### 14.2 不建议回传的内容

- 实时视频推理结果
- 每帧图片
- 海量检测框
- 在线业务流水

### 14.3 查看位置

回传后的内容可在 ClearML 中查看：

- Scalars：FPS / Latency / mAP
- DEBUG SAMPLES：预测样例图
- ARTIFACTS：预测结果文件、评测结果文件

---

## 15. ONNX 与训练任务的关联方式

当使用 YOLO + ClearML 训练后，训练任务已存在，导出 ONNX 时需要把 ONNX 和原训练实验关联起来。

推荐两种方式：

### 15.1 方式一：ONNX 挂到原训练 Task

适合需求：

- 希望 ONNX 在原训练实验下直接可见。

做法：

- 复用原训练 Task，上传 ONNX 作为 OutputModel 或 Artifact。

### 15.2 方式二：单独创建“导出 ONNX”Task

适合需求：

- 希望训练、导出、转换链路更清晰。
- 后续还要扩展 TensorRT、RKNN、海思、联咏等下游任务。

做法：

- 创建一个新的导出 Task。
- 记录其来源训练 Task ID。
- 把 ONNX 作为该导出 Task 的输出模型。
- 在自研数据库中维护上下游血缘关系。

### 15.3 建议

如果后续流程会继续延伸到多种转换任务，优先采用“单独导出 Task”的方式，便于形成完整血缘：

```text
训练任务
  ↓
导出 ONNX 任务
  ↓
海思转换任务
  ↓
联咏转换任务
  ↓
评测任务
```

---

## 16. 一期 MVP

### 16.1 一期目标

一期不追求完整平台，只打通以下最小闭环：

```text
自研平台点按钮
  ↓
创建 ClearML 导出任务
  ↓
Agent 执行
  ↓
产物回传
  ↓
平台展示
```

推荐第一阶段闭环：

```text
PT -> ONNX
```

### 16.2 一期页面流程

```text
训练任务详情
  ↓
点击【导出 ONNX】
  ↓
填写 imgsz / opset / dynamic / simplify
  ↓
创建 ClearML Task
  ↓
Agent 执行
  ↓
ONNX 文件回传
  ↓
平台显示 best.onnx
```

### 16.3 一期验收标准

一期完成后，至少应满足以下验收条件：

1. 平台可展示训练任务列表，且数据来自自研数据库。
2. 训练任务详情页可展示基础信息、当前状态、关键指标和 ClearML 任务标识。
3. 用户可在训练任务详情页点击“导出 ONNX”并提交参数。
4. 平台可成功创建 ClearML 导出任务，并保存导出任务记录。
5. 平台可同步导出任务状态变化，至少覆盖 `queued / running / succeeded / failed`。
6. 导出成功后，平台可展示 ONNX 文件信息和下载/查看入口。
7. 导出失败后，平台可展示失败状态、失败原因和 ClearML 日志入口。
8. 对同一个导出任务重复同步不会产生重复记录。

---

## 17. 分阶段建设路线

### 第一阶段

- 建业务数据模型
- 建 ClearML 同步服务
- 打通 PT -> ONNX 闭环

### 第二阶段

- 建模型仓库
- 增加“注册为模型版本”
- 建版本详情页

### 第三阶段

- 增加 ONNX -> 海思 / 联咏 / RKNN 转换任务
- 建转换记录与任务血缘

### 第四阶段

- 增加调试预测与离线评测
- 先做单图调试预测
- 再做数据集评测、视频预测、RTSP 预测、多模型对比

---

## 18. 最终结论

本需求的核心判断如下：

1. 需要自研 MLOps 平台，但不重写 ClearML。
2. ClearML 作为底层执行与追踪引擎，自研平台作为主业务入口。
3. 训练任务与模型仓库必须分层，不能把每次训练都直接当模型版本。
4. 模型仓库应采用“算法模型 -> 模型版本 -> 模型文件”三级结构。
5. 导出、转换、离线评测等耗时且需要留痕的任务，优先走 ClearML Task。
6. 在线推理应走自研 REST API，而不是走 ClearML 实时主链路。
7. 第一优先级是打通 `ClearML 同步服务 + PT 导出 ONNX` 的最小闭环。

---

## 19. 来源与说明

本文档整理自以下讨论内容：

- ChatGPT 分享链接：<https://chatgpt.com/share/6a238505-6574-83e8-9307-170000b1f5fb>

说明：

- 文档中的“建议”“推荐”属于整理后的方案判断。
- 文档中的“一期范围”“一期验收标准”属于当前建议确认项。
- 若后续评审有调整，应优先修改范围、数据模型和验收标准三部分。
