# MLOps REST API 文档

版本：`phase-1`

本文档描述当前自研后端对外提供的 REST API。所有接口都以统一响应封装返回，前端应按本文档定义的字段组装页面和表单。

## 1. 通用约定

### 1.1 Base URL

本地开发默认：

```text
http://127.0.0.1:18087
```

### 1.2 统一成功响应

所有成功响应都使用统一 envelope：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "optional-request-id",
  "warnings": []
}
```

字段说明：

- `code`：成功时固定为 `0`
- `message`：成功时固定为 `success`
- `data`：业务数据
- `request_id`：请求链路 ID，由后端生成并透传到响应头 `X-Request-ID`，用于排查问题
- `warnings`：非致命告警列表，适合展示在页面顶部或提交结果提示区

### 1.3 统一错误响应

错误响应使用统一 envelope：

```json
{
  "code": 40001,
  "message": "human readable message",
  "details": {},
  "request_id": "optional-request-id"
}
```

常见错误码：

- `40001`：模板不存在
- `40002`：训练任务不存在
- `40003`：领域校验失败
- `50201`：ClearML 适配层异常
- `50000`：内部服务器错误

字段说明：

- `code`：错误码，统一使用整数
- `message`：面向人的错误描述
- `details`：可选的结构化错误细节，通常用于附加校验错误、第三方异常摘要或调试上下文
- `request_id`：请求链路 ID，便于把前端报错和后端日志关联起来

### 1.4 参数分组

创建类接口统一将参数分为两组：

- `params`
  - 业务参数
  - 例：`data`、`project`、`epochs`、`batch`、`imgsz`
- `execution_params`
  - 执行参数
  - 例：`nproc_per_node`、`cuda_visible_devices`

前端应把这两组参数分开展示和提交。后端会在下发 ClearML 任务时合并处理，但不会把执行参数当作真实训练脚本的业务参数语义。

### 1.5 告警与错误的使用边界

- 需要展示给用户但不阻断流程的提示，放在顶层 `warnings`
- 需要让程序判断并拦截的错误，放在错误响应的 `code`
- `details` 用于补充结构化调试信息，不作为页面主文案来源

---

## 2. 系统接口

### 2.1 GET `/mlops/system/health`

检查服务是否存活。

#### Response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok",
    "app_name": "mlops-backend"
  },
  "request_id": "..."
}
```

#### 字段说明

- `data.status`：固定为 `ok`
- `data.app_name`：应用名称，来自配置文件

### 2.2 GET `/mlops/system/runtime`

查询运行时状态，目前主要返回调度器状态。

#### Response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "scheduler": {
      "enabled": true,
      "running": true,
      "job_count": 1
    }
  },
  "request_id": "..."
}
```

#### 字段说明

- `scheduler.enabled`：调度器是否启用
- `scheduler.running`：调度器当前是否运行
- `scheduler.job_count`：当前已注册的调度任务数量

---

## 3. 训练接口

### 3.1 GET `/mlops/training`

分页查询训练任务。

#### Query 参数

- `page`：页码，默认 `1`
- `page_size`：每页条数，默认 `20`，最大 `200`
- `status`：按状态过滤，可选

#### Response `data`

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

`items` 中每一项包含：

- `id`
- `parent_task_id`
- `task_name`
- `task_group`
- `task_type`
- `task_source`
- `status`
- `clearml_task_id`
- `queue_name`
- `template_name`
- `params`
- `parameter_snapshot`
- `runtime_snapshot`
- `custom_data`
- `result_summary`
- `error_message`
- `last_sync_status`
- `last_sync_error`
- `sync_version`
- `created_at`
- `updated_at`

### 3.2 GET `/mlops/training/create-meta`

获取训练创建页所需的元信息。

#### Response `data`

```json
{
  "templates": [
    {
      "name": "convnext-default",
      "display_name": "Convnext Default",
      "queue": "train_convnext",
      "entrypoint": "/mnt/sdb/yufl/mlops_tools/generic_clearml_wrapper.py",
      "defaults": {
        "data": "/mnt/imgs_coco_datasets_145/2026_imgs_datasets/imgs_cls_vehicle_10class/imgs_cls_vehicle_10class_baseline/",
        "project": "classify_vehicle_10class",
        "epochs": 1,
        "batch": 64,
        "imgsz": 224
      },
      "runtime": {
        "launcher": "torchrun",
        "script_path": "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls/tools/train.py",
        "working_dir": "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls",
        "env": {
          "NCCL_P2P_DISABLE": 0,
          "NCCL_IB_DISABLE": 1
        },
        "artifacts": [
          {
            "name": "best_model",
            "role": "model_weight",
            "format": "pth",
            "path": "{output_dir}/best.pth"
          },
          {
            "name": "train_metrics",
            "role": "metrics",
            "format": "csv",
            "path": "{output_dir}/results.csv"
          },
          {
            "name": "final_summary",
            "role": "summary",
            "format": "json",
            "path": "{output_dir}/final_summary.json"
          }
        ]
      },
      "execution_defaults": {
        "nproc_per_node": 1,
        "cuda_visible_devices": "2"
      }
    }
  ],
  "queues": [
    {
      "queue_name": "train_convnext",
      "agent_count": 1,
      "has_online_agents": true,
      "agents": [
        {
          "name": "clearml-agent-1",
          "status": "online"
        }
      ],
      "last_seen": "2026-06-08T00:00:00Z"
    }
  ]
}
```

#### 字段说明

`templates[]`：

- `name`：模板名称
- `display_name`：展示名称
- `queue`：目标队列名
- `entrypoint`：执行入口
- `defaults`：业务参数默认值
- `execution_defaults`：执行参数默认值

`queues[]`：

- `queue_name`：队列名称
- `agent_count`：关联 Agent 数量
- `has_online_agents`：是否存在在线 Agent
- `agents`：Agent 列表
- `last_seen`：最近在线时间

### 3.3 GET `/mlops/training/{task_id}`

获取单个训练任务详情。

#### Path 参数

- `task_id`：本地任务 ID

#### Response `data`

任务结构与 `GET /training` 的 item 一致。

#### 404

当任务不存在或不是训练任务时，返回：

```json
{
  "code": 40002,
  "message": "Training task '123' was not found"
}
```

### 3.4 POST `/mlops/training`

创建训练任务并下发到 ClearML。

#### Request Body

```json
{
  "task_name": "convnext-exp-20260608",
  "template_name": "convnext-default",
  "params": {
    "data": "/mnt/imgs_coco_datasets_145/2026_imgs_datasets/imgs_cls_vehicle_10class/imgs_cls_vehicle_10class_baseline/",
    "project": "classify_vehicle_10class",
    "epochs": 1,
    "batch": 64,
    "imgsz": 224
  },
  "execution_params": {
    "nproc_per_node": 1,
    "cuda_visible_devices": "2"
  },
  "queue_name": "train_convnext",
  "custom_data": {
    "source": "ui"
  }
}
```

#### 字段说明

- `task_name`：平台任务名称
- `template_name`：模板名称
- `params`：业务参数
- `execution_params`：执行参数
- `queue_name`：可选，覆盖模板默认队列
- `custom_data`：可选自定义数据

#### Response `data`

```json
{
  "task": {
    "id": 1,
    "task_name": "convnext-exp-20260608",
    "task_group": "training",
    "task_type": "training",
    "task_source": "platform",
    "status": "queued",
    "clearml_task_id": "8db333699f8742f78ba99f78ab6d3fa7",
    "queue_name": "train_convnext",
    "template_name": "convnext-default",
    "params": {},
    "parameter_snapshot": {},
    "runtime_snapshot": {},
    "custom_data": {},
    "result_summary": {},
    "error_message": null,
    "last_sync_status": null,
    "last_sync_error": null,
    "sync_version": 1,
    "created_at": "2026-06-08T05:10:08.112786",
    "updated_at": "2026-06-08T05:10:08.112789"
  },
  "submission": {
    "clearml_task_id": "8db333699f8742f78ba99f78ab6d3fa7",
    "status": "queued"
  }
}
```

#### Warnings

如果目标队列没有在线 Agent，响应顶层 `warnings` 会返回告警，例如：

```json
[
  "Queue 'train_convnext' has no online agents. The task will remain queued until an agent comes online."
]
```

---

## 4. 转换接口

### 4.1 POST `/mlops/conversion/onnx`

创建 `PT -> ONNX` 导出任务。

#### Request Body

```json
{
  "parent_task_id": 1,
  "task_name": "train-smoke-export-onnx",
  "params": {
    "opset": 17,
    "dynamic": false
  },
  "execution_params": {
    "nproc_per_node": 1
  }
}
```

#### 字段说明

- `parent_task_id`：来源训练任务的本地 ID
- `task_name`：可选，导出任务名
- `params`：导出业务参数
- `execution_params`：导出执行参数

#### 响应说明

响应结构与训练创建一致：

- `task`：导出任务本地记录
- `submission`：ClearML 提交摘要
- `warnings`：顶层告警列表

#### 约束

- `parent_task_id` 必须对应一个已存在的训练任务
- 如果父任务不存在，返回 400
- 如果父任务不是训练任务，返回 400

---

## 5. 状态与行为约定

### 5.1 训练任务状态

当前平台不在本地模拟执行状态机，任务状态以 ClearML 和同步逻辑为准。常见状态包括：

- `queued`
- `in_progress`
- `completed`
- `failed`

### 5.2 告警规则

以下场景会通过顶层 `warnings` 返回告警，而不是直接失败：

- 目标队列没有在线 Agent
- ClearML 侧部分可选信息缺失，但任务创建成功

### 5.3 参数分组规则

前端和调用方应遵循：

- `params` 只放业务参数
- `execution_params` 只放执行参数

后端会把这两部分分别写入 ClearML 的 `Args` 和 `Runtime` section。
`Runtime.execution_params` 只供 wrapper 使用，不会转发给真实脚本。
`Runtime.artifacts` 定义任务成功后需要上传到 ClearML 的产物文件和元信息。

---

## 6. 示例调用

### 6.1 创建训练任务

```bash
curl -X POST "http://127.0.0.1:18087/mlops/training" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "convnext-exp-20260608",
    "template_name": "convnext-default",
    "params": {
      "data": "/mnt/imgs_coco_datasets_145/2026_imgs_datasets/imgs_cls_vehicle_10class/imgs_cls_vehicle_10class_baseline/",
      "project": "classify_vehicle_10class",
      "epochs": 1,
      "batch": 64,
      "imgsz": 224
    },
    "execution_params": {
      "nproc_per_node": 1,
      "cuda_visible_devices": "2"
    }
  }'
```

### 6.2 创建 ONNX 导出任务

```bash
curl -X POST "http://127.0.0.1:18087/mlops/conversion/onnx" \
  -H "Content-Type: application/json" \
  -d '{
    "parent_task_id": 1,
    "task_name": "train-smoke-export-onnx",
    "params": {
      "opset": 17,
      "dynamic": false
    },
    "execution_params": {
      "nproc_per_node": 1
    }
  }'
```

---

## 7. 备注

- 本文档按当前一期后端实现编写
- 如果后续新增 YOLO、评测、ONNX -> 海思等任务类型，建议继续沿用 `params` + `execution_params` 的分组方式
- 前端实现前，应先对照本文档完成表单字段映射
