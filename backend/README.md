# MLOps Backend

本目录是后端服务的运行入口。当前项目约定是：

- 先进入 `backend/` 目录
- 再使用本目录下的 `.venv` 执行代码

这样可以保证配置文件、模板文件和数据库相对路径都按当前代码约定正确解析。

## 运行环境

需要 Python 3.12 或更高版本。首次使用时，在 `backend/` 目录中创建 `.venv` 并安装项目及开发依赖：

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e '.[dev]'
```

安装完成后可检查虚拟环境中的 Python 版本：

```bash
cd backend
./.venv/bin/python --version
```

## 启动服务

```bash
cd backend
./.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 18087
./.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 18087
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

## 联咏692模型导出

在实验模型列表中选择 ONNX 的“联咏692”入口，提交后可在转换记录中查看日志、下载生成的 `.bin`，并沿用现有 692 打包功能。

运行配置位于 `config/app.yaml` 的 `model_conversion.converters.onnx_to_novatek692`，包括脚本路径、Docker 镜像和 Novatek 工具目录。后端执行用户需要能够运行本机 Docker，且 Docker 主机必须能访问后端使用的模型和量化路径。

量化目录自动按 `quantization_dataset.storage_root / project.project` 解析，其中 `project.project` 是模型族标识。例如根目录为 `./data/quantization-datasets`，模型族为 `classify_twowheel`，实际目录为 `backend/data/quantization-datasets/classify_twowheel`。相对根目录以配置文件所在目录的上一级（通常为 `backend/`）解析，不从请求接收自定义量化路径。

该目录须准备 `config/cnn25/gen_config.txt`、`config/cnn25/sim_config.txt`、`config/mean_data.txt` 和非空 `ref_img_list.txt`。配置中的模型及输出目录应指向容器内 `/exp/novaic_output`；量化目录按原绝对路径只读挂载，图片列表中的路径须在容器内可访问。平台不自动改写预处理配置和图片列表。

平台默认参数为 `chip=690`、`op_mode=2`、`bit_mode=1`、`quan_scheme=1`、`use_onnx=true`、`stripe_perfmode=1`、`vlc_en=1`。每项任务使用独立临时实验目录调用脚本，仅在退出码正常且 `novaic_output/sdk/nvt_model.bin` 非空时替换目标文件；失败保留原目标文件，日志保存在实验目录。无需数据库迁移。

## RK3588 模型导出

ONNX 模型的“RK3588”入口调用独立脚本 `scripts/model_conversion/rknn/export_rknn.py`。转换器为 `onnx_to_rk3588`，复用转换队列、日志、文件列表和 3588 打包，无需数据库迁移。页面精度默认选中 INT8，可选择 FP16、INT8 或混合量化（INT8 + FP16）。INT8 和混合量化均需选择校准数据集；混合量化使用已验证的 Toolkit 自动混合量化 `auto_hybrid=True`。CLI 使用 `--precision hybrid`；为兼容已有调用，API 和 CLI 省略精度时仍为 FP16。配置在 `config/app.yaml`，默认解释器为 `/mnt/yolo_tool/envs/rknn-env/bin/python`；后端环境不需要安装 RKNN。

可先通过命令行独立导出，例如输入为 RGB、像素除以 255 的 YOLO 模型：

```bash
/mnt/yolo_tool/envs/rknn-env/bin/python -u scripts/model_conversion/rknn/export_rknn.py \
  --onnx /absolute/path/best.onnx \
  --output /absolute/path/best_3588.rknn \
  --precision fp16 --mean 0,0,0 --std 255,255,255 \
  --color-order rgb --resize-mode letterbox
```

INT8 改为 `--precision int8`，并增加 `--dataset-dir /absolute/path/images --max-samples 200`。按文件路径排序选取校准图片，`--max-samples 0` 使用全部图片。脚本重新生成校准清单，不依赖其他平台的 `ref_img_list.txt` 或配置文件。平台仅接收量化数据集 ID，不接收任意服务器目录；旧工作区记录不存在且原数据根目录名称相同时，按数据集目录名映射到当前存储根目录，不修改数据库原记录。

首版支持 float32 ONNX、单输入、NCHW、batch=1、三通道图像。固定输入从 ONNX 读取；动态输入需用 `--input-shape images:1,3,640,640` 指定实际名称和尺寸，不可覆盖模型已固定的维度。多输入及其他布局暂不支持。转换不自动重写 YOLO 输出节点或后处理，部署程序必须匹配导出的输出结构。

预处理公式为 `(pixel - mean) / std`。CLI 默认 mean=0、std=1，分类模型请按实际训练配置填写；界面对未知模型不预填归一化参数。颜色顺序与缩放设置用于生成校准图片，不会把颜色转换或 resize 插入模型；板端必须使用相同的颜色、缩放策略，且避免重复归一化。`letterbox` 为线性插值、居中补边、填充值 114。若业务需要 center crop 等其他预处理，应先准备符合该流程的校准图片。

任务及脚本使用独立临时工作目录，逐步检查工具链返回码；仅成功生成非空 `.rknn` 才发布文件。默认拒绝覆盖，CLI 显式传 `--overwrite` 可覆盖。后端日志位于实验目录，包含工具链版本、参数、输入输出名称、源模型和校准图片 SHA256。转换成功仅表示文件生成成功，板端 Runtime/驱动兼容性和业务精度应另外验证。

安装时使用工具链中匹配 Python 版本的 wheel 与 requirements；ONNX 转换可使用 CPU 版 PyTorch。当前工具目录有 Toolkit2 2.5.0 / CPython 3.12 wheel。板端初始检查发现系统 Runtime 1.6.0、驱动 0.7.2；不要未经验证直接替换生产系统库。

RKNN Toolkit2 2.5.0 初始化仍依赖 `pkg_resources`，需额外安装 `setuptools<81`（约束见 `scripts/model_conversion/rknn/constraints.txt`）；仅 `pip check` 通过不足以确认转换环境可用，需要实际创建 `RKNN()` 并执行转换。

2026-11-12 实测：HGNet 分类模型的 FP16 / INT8 均在系统 Runtime 1.6.0、驱动 0.7.2 上完成推理；单张样本 top-1 与 ONNX 一致，输出余弦相似度分别约 0.99999988 / 0.99949205。这是链路与数值冒烟验证，不代表完整验证集精度验收（INT8 本次仅用 20 张校准图片）。

标准 YOLOv8 `[1,84,8400]` 输出模型在当前 Toolkit2 2.5.0 下触发 `REGTASK ... exceeds the limit`（8191 / 8399），即使 `build()` 返回 0 也会产生错误结果。换 Runtime 2.5.0、关闭优化、改成外部归一化 float32 输入均未解决。脚本现在逐行检查原生编译输出，发现寄存器溢出或 `E RKNN:` 错误即拒绝发布产物，并保留原目标文件。此类模型需使用与板端后处理匹配的 RKNN 专用 ONNX 或另行验证兼容工具链，不能把当前标准 ONNX 直接视为可部署模型。

上述 YOLO 冒烟样本的来源是 `/mnt/yolo_tool/novatek/test_remove_op/yolo/yolov8n.onnx`，输出为 80 类标准检测头；校准图片来自 `detect_6class`。此测试不能替代业务 6 分类 YOLO 的兼容性或精度验证。Toolkit2 2.5.0 在实测正常的 HGNet 模型上也输出 `Unkown op target: 0` 诊断，脚本保留该日志但仅对此条已验证诊断例外处理，其他原生错误仍会拦截。

补测业务 6 分类模型 `.../ultralytics-main-yolov26/runs/detect/detect_6class/yolov8n_20261101_exp/weights/best.onnx`（输出 `[1,10,8400]`）时，Toolkit2 2.5.0 在加载阶段报 `Unsupport onnx opset 20, need <= 19!`。需从原权重重新导出兼容 opset 后继续验证，不能直接改写 ONNX 的版本号。本次未对该业务模型作可部署或精度通过的结论。

### YOLOv8 业务模型适配

RK3588 导出抽屉新增“输出格式”：默认保留原始 ONNX 输出；针对标准 YOLOv8 检测模型，可显式选择“YOLOv8 三尺度检测头（9 输出）”。CLI 对应 `--profile yolov8`，例如：

```bash
/mnt/yolo_tool/envs/rknn-env/bin/python -u scripts/model_conversion/rknn/export_rknn.py \
  --onnx /absolute/path/best.onnx --output /absolute/path/best_3588_fp16.rknn \
  --profile yolov8 --precision fp16 --mean 0,0,0 --std 255,255,255 \
  --color-order rgb --resize-mode letterbox
```

该模式直接读取现有 ONNX，提取 cv2/cv3 三尺度检测头，再用 ONNX 官方版本转换器将提取后的图降至 opset 19（仅在源版本更高时），不直接修改版本号，也不覆盖原模型。模型需固定 NCHW / batch=1，stride 为 8、16、32；不适用于 YOLO26、分割、多输入或无法识别检测头的自定义结构，遇到这些结构明确报错。

每个尺度输出依次为：`boxes`（DFL 分布）、`scores`（类别概率）、`score_sum`（类别概率和，截断到 0～1）。共九个输出，布局为 NCHW。`yolov8_postprocess.py` 的 `decode(outputs)` 将反量化后的浮点输出恢复为原始 `[1,4+类别数,候选框数]` 的 xywh + 类别概率；之后还需业务已有的置信度过滤、按类别 NMS 和 letterbox 坐标还原。INT8 原生输出必须先按各输出张量的 zero-point/scale 反量化，或用 Runtime 的 `want_float=1`。不得把九输出模型直接交给原先单输出模型的后处理。

也可先独立执行 `prepare_yolov8_rknn.py --onnx best.onnx --output best_rk3588.onnx`，检查生成的 ONNX 后再以默认 `--profile generic` 转换，避免重复适配。适配方式依据本机 Rockchip YOLOv8 示例的检测头约定，验证记录见 `docs/rknn-business-validation-20261112.json`。

2026-11-12 后续业务验证已完成：直接以 `yolov8n_20261101_exp/weights/best.onnx` 为源，使用 `--profile yolov8` 成功生成 FP16 / INT8，在原有板端 Runtime 1.6.0、驱动 0.7.2 上推理，无需替换系统库。5 张未参与校准的图片上，原 ONNX 有 58 个检测；FP16 的 58 个检测全部匹配，匹配框平均 IoU 0.99424。INT8 用 200 张图片校准后得到 54 个检测，其中 53 个同类别且 IoU≥0.5 的匹配，仍有量化偏差，因此当前优先使用 FP16。上述仅为小样本 ONNX 一致性测试，不是完整验证集 mAP 验收。

验证产物已保存到该实验的 `weights/` 下：`best_rk3588.onnx`、`best_rk3588_fp16.rknn`、`best_rk3588_int8.rknn`、`best_rk3588_postprocess.py`，另有 manifest、validation JSON 和转换日志。原 `best.onnx` 的 SHA256 保持不变。完整记录见仓库 `docs/rknn-business-validation-20261112.json`。
