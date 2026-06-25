# MLOps Backend

本目录是后端服务的运行入口。当前项目约定是：

- 先进入 `backend/` 目录
- 再使用本目录下的 `.venv` 执行代码

这样可以保证配置文件、模板文件和数据库相对路径都按当前代码约定正确解析。

## 运行环境

建议使用项目内虚拟环境：

```bash
cd backend
./.venv/bin/python --version
```

## 启动服务

```bash
cd backend
./.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 18087
```

说明：

- 默认配置文件是 [`backend/config/app.yaml`](./config/app.yaml)
- 默认训练模板文件是 [`backend/config/training-templates.yaml`](./config/training-templates.yaml)
- 默认转换模板文件是 [`backend/config/conversion-templates.yaml`](./config/conversion-templates.yaml)

## 运行测试

```bash
cd backend
./.venv/bin/python -m pytest -q
```

当前代码库里，测试是按 `backend/` 目录语义编写和执行的。

### 冒烟测试

```bash
cd backend
./.venv/bin/python -m pytest tests/test_health_smoke.py -q
```

这组测试会覆盖：

- `/mlops/system/health`
- `/mlops/system/runtime`
- `/mlops/datasets`
- `/mlops/training/create-meta`
- `/mlops/training`
- `/mlops/training/{task_id}`
- `/mlops/training`
- `/mlops/conversion/onnx`

## 配置说明

默认配置来自 [`backend/config/app.yaml`](./config/app.yaml)。

如果需要覆盖配置文件路径，可以设置环境变量：

```bash
cd backend
export MLOPS_BACKEND_CONFIG_PATH=./config/app.yaml
```

常见配置项：

- `app.api_prefix`：后端对外暴露的统一 API 前缀，例如 `/mlops`
- `app.root_path`：反向代理/网关挂载路径，直接本地访问时通常留空
- `database.url`：一期 SQLite 数据库地址
- `templates.training`：训练模板 YAML 路径
- `templates.conversion`：转换模板 YAML 路径
- `clearml.mode`：`stub` 或 `http`
- `clearml.api_base_url`：ClearML API 地址
- `clearml.access_key` / `clearml.secret_key`：ClearML REST API 凭据，仅在 `clearml.mode=http` 时需要

## 常见操作

### 查看 API 文档

服务启动后访问：

- `http://127.0.0.1:18087/docs`
- `http://127.0.0.1:18087/openapi.json`

### 数据集管理接口

当前后端已提供数据集管理菜单所需的基础接口：

- `GET /mlops/datasets`
  返回数据集列表
- `GET /mlops/datasets/{dataset_id}`
  返回单条数据集详情
- `POST /mlops/datasets`
  创建数据集
- `PUT /mlops/datasets/{dataset_id}`
  修改数据集
- `DELETE /mlops/datasets/{dataset_id}`
  物理删除数据集

数据集接口的主要字段约定：

- `name`
  数据集名称，唯一
- `path`
  本地绝对路径，唯一
- `task_type`
  任务类型，可空，由前端页面下拉框提交
- `class_names`
  类别名称数组，直接返回给前端，不额外派生 `class_count`
- `description`
  描述/备注，可空
- `created_at` / `updated_at`
  创建时间和修改时间

示例创建请求：

```json
{
  "name": "vehicle-10class",
  "path": "/mnt/datasets/vehicle_cls",
  "task_type": "classification",
  "class_names": ["car", "bus", "truck"],
  "description": "车型分类基线数据集"
}
```

### 执行数据库迁移

如果需要手动跑 Alembic：

```bash
cd backend
./.venv/bin/alembic upgrade head
```

## 当前约定

- 路由层只负责请求和响应，不直接操作数据库
- 训练任务通过 YAML 模板创建
- `PT -> ONNX` 导出任务作为训练任务的 `child task`
- ClearML 负责任务执行、日志、指标和产物
- 自研后端负责统一入口、业务状态和数据展示
- 训练和导出任务统一通过远端挂载目录中的 `entrypoint.py` 启动，脚本在 `convnext-env` 里读取 ClearML 任务的 `Args` 和 `Runtime` 两个 section
- `Runtime.execution_params` 只给 wrapper 用，不会转发给真实训练/导出脚本
- `Runtime.artifacts` 定义需要在任务成功后上传到 ClearML 的产物文件路径、名称和元信息
- `convnext-default` 的真实训练脚本仍然由模板中的 `Runtime.script_path` 决定
- 像 `nproc_per_node`、`cuda_visible_devices` 这类执行参数可以和业务参数一起从页面传入，但会以 `Runtime.execution_params` 的形式下发
- 训练创建请求建议使用 `params` 和 `execution_params` 分组，前者放业务参数，后者放执行参数
