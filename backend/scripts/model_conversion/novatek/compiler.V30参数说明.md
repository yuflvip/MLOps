# compiler.V30 参数及中文说明

- 整理日期：2026-10-29
- 适用工具：联咏 Novaic CNN30 `closeprefix/bin/compiler.V30`
- 发布版本：`release_v04.01.250807.00`
- 核对环境：服务器现有容器 `ubuntu20p04-novatek`，镜像 `ubuntu20p04:202407013`
- 信息来源：服务器实际执行的 `compiler.V30 --help`，以及同版本《Novaic Convertor User Guide》英文版。
- 本次仅整理资料，没有执行模型转换。

## 1. 阅读说明

本文完整整理本次实际 `--help` 输出中列出的参数，并单独列出手册补充项。它不保证涵盖二进制未公开的隐藏参数。

- `<整数>`、`<目录>`、`<字符串>`等是占位说明，调用时替换成实际值。
- “开关”表示直接写参数名，不需要在后面填写 `1`。
- 参数值、默认值或行为未在来源中明确时，本文不会推测。
- 实际帮助与手册有差异的地方见“文档差异与适用限制”。
- 所有模型、配置、校准数据及输出路径，都必须是容器内部可访问的路径。

主要手册位置：

`Doc/Tool/Novaic_Convertor_User_Guide_en.pdf`

主要依据章节：第 31 页路径配置，第 47～52 页精度配置，第 76～81 页输入输出文件，第 97～107 页 Gen-tool 命令参数，以及大模型转换章节。

## 2. 基本调用与日志参数

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--help` | 开关 | 显示当前程序帮助。 |
| `--config-dir` | `<目录>` | 配置根目录，包含 `config`、`input` 等子目录。必填。可使用绝对路径或相对于 toolchain 的路径。 |
| `--pattern-name` | `<名称>` | 网络／任务名称，用于定位 `config-dir/config/任务名称/`。必填。服务器现有脚本使用 `.`。 |
| `--chip` | `<芯片编号>` | 当前 V30 帮助列出 `690`、`538`、`539A`、`635`、`533`。需与目标平台及仿真配置一致。 |
| `--verbose` | `0～4` | 日志等级：`0` FATAL、`1` ERROR、`2` WARNING、`3` INDEX、`4` USER。默认 `4`。 |
| `-v` | 开关，可重复 | 每增加一个 `-v`，日志等级提高一级。 |
| `--quiet` | 开关 | 将日志等级设为 `0`。 |
| `--no-file-op` | `0／1` | 控制无文件输出机制，还受编译时 `NO_FILE_OP` 宏影响。`0` 明确允许文件输出；`1` 是否禁止输出取决于编译设置。不能直接理解为任何版本都不落盘。 |
| `--openmp-en` | `<线程数>` | OpenMP 加速：`0` 关闭，正整数表示开启并指定线程数。应结合服务器可用 CPU 资源设置。 |
| `--measure-time` | 开关 | 统计模型转换各阶段耗时。 |

## 3. 模型输入与 ONNX 转换

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--use-caffe` | 开关 | 使用 Caffe 模型并调用相应前端转换流程。 |
| `--use-onnx` | 开关 | 对原始 ONNX 执行联咏前端转换，包含检查及简化。手册约定原始文件名为 `deploy_float.onnx`。 |
| `--use-onnx-nosim` | 开关 | 使用 ONNX 前端转换，但跳过 onnxsim 简化。 |
| `--use-tflite` | `<整数>` | 使用 TFLite 模型；当前帮助未给出完整枚举和限制。 |
| `--onnx-batch` | `0／1` | batch 来源：`0` 使用模型中的 batch，默认；`1` 使用 gen_config 中的 batch。不是直接填写 batch 数量。 |
| `--onnx-input-shape` | `<字符串>` | 指定 ONNX 输入形状，可按输入名填写 JSON 字符串。输入名必须与模型一致。 |
| `--use-top-name` | 开关 | 使用节点 top 名称作为节点输出名称，帮助未进一步解释命名细节。 |
| `--keep_output_name` | 开关 | 保留原始输出层名称。手册要求配合 `--use-onnx` 使用。参数名使用下划线。 |
| `--remain-pat-name` | `0／1` | 是否保持 pattern 名称不变：`0` 关闭，`1` 开启。 |
| `--write-float-fixed-info` | 开关 | 将模型输入／输出属于浮点还是定点的信息写入外部信息块，供 SDK 获取。 |

输入形状示例：

```bash
--onnx-input-shape '{"images":[1,3,224,224]}'
```

以上 `images` 必须替换为模型实际输入名。

## 4. 位宽、量化与精度

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--bit-mode` | `<整数>` | 权重与激活位宽策略，详见位宽表。 |
| `--calib-mode` | `0～4` | 校准算法：`0` Max；`1` L2；`2` KLD；`3` Clip；`4` Percentile。 |
| `--quan-scheme` | `0～3` | 量化粒度：`0` 按张量；`1` 权重按通道；`2` 权重和激活均按通道；`3` 两者按通道并结合 SmoothQuant。手册对 `1` 具体描述为卷积权重按通道。 |
| `--clamp-quan-parm` | `0／1` | 量化参数超出硬件规格时：`0` 报断言错误，默认；`1` 截断到允许范围。 |
| `--use-qat` | `0／1／9` | `0` 普通 ONNX，默认；`1` Nova 格式模型；`9` QIR 格式模型。不能据此认定任意框架导出的 QAT ONNX 均兼容。 |
| `--cust-quan-mode` | `0～3` | `0` 普通模式；`1` 导出量化信息；`2` 注入量化信息；`3` 自动注入模式。 |
| `--cust-quan-path` | `<目录>` | 量化信息文件 `quan_info.json` 的存放／读取目录。 |
| `--cust-quan-val-mode` | `0～2` | 量化信息表示方式：`0` Max-Min；`1` Scale-Zeropoint；`2` BitDepth。 |
| `--quick-infer` | `<浮点数>` | 快速推理／校准：`0` 关闭；`0～100` 之间表示采用 N% patch 推理。帮助未说明端点 `100` 的行为。 |
| `--mp-thld` | `0～1` | 混合精度阈值／比例，需配合自动位宽和对应混合精度方法使用。手册说明在对应模式下，`0` 相当于全 8 bit，`1` 相当于全 16 bit。 |
| `--mp-method` | `<整数>` | 混合精度算法，帮助列出 `0、1、10、11、12`；手册另列 `20、21、22`。详见后表。 |
| `--easy-quant-mode` | `0／1` | 是否启用 EasyQuant 权重量化优化。 |
| `--bias-correction` | `0／1／2` | 偏置校正模式；当前帮助未解释 `1`、`2` 的算法差异。 |
| `--cle-en` | `<整数>` | 跨层均衡 CLE：`0` 使用工具默认设置；`1` 开启。 |
| `--smoothquant-en` | `<整数>` | SmoothQuant 参数。帮助写 `50` 为工具默认值，手册说明可在 `50～70` 调整权重与激活之间的比例。 |
| `--meansub-dc` | 开关 | 强制均值减法使用 DC 模式，对应 `[preproc/meansub/mode] = 0`。 |
| `--bit24-kernel-thld` | `1.0～10.0` | 帮助描述为新旧 kernel 大小比例阈值；手册描述为限制激活变为 4 bit 时的带宽增幅，默认 `3.0`，仅适用于位宽模式 `5／7`。两处表述有差异。 |
| `--4a8w-opt-mode` | `0／1` | 4 bit 激活、8 bit 权重时：`0` 带宽优先；`1` 执行时间优先。帮助和手册对默认值描述冲突，应显式设置。 |

### 4.1 bit-mode 位宽表

W 为权重，A 为激活／特征。

| 值 | 权重 W | 激活 A | 说明 |
| --- | --- | --- | --- |
| `0` | 自动 | 自动 | 自动混合精度。 |
| `1` | 8 bit | 8 bit | 8W8A，手册标为默认。 |
| `2` | 16 bit | 16 bit | 16W16A。 |
| `3` | 8 bit | 16 bit | 8W16A，服务器现有 8w16a 脚本使用此值。 |
| `4` | 16 bit | 8 bit | 16W8A。 |
| `5` | 4 bit | 4 bit | 手册补充，实际帮助未展开。 |
| `6` | 4 bit | 8 bit | 手册补充，实际帮助未展开。 |
| `7` | 8 bit | 4 bit | 手册补充，实际帮助未展开。 |

手册明确说明 NT98533 暂不支持 `5～7`。本文未实际验证任何 4 bit 模式。

### 4.2 混合精度方法

| mp-method | 中文说明 | 来源 |
| --- | --- | --- |
| `0` | 均方误差 MSE，手册标为默认。 | 帮助＋手册 |
| `1` | OMPQ 敏感度方法。 | 帮助＋手册 |
| `10` | 根据输出余弦相似度／差异进行混合精度分析。 | 帮助＋手册 |
| `11` | 根据输出余弦相似度分析。 | 帮助＋手册 |
| `12` | 根据输出平均差异分析。 | 帮助＋手册 |
| `20` | 类似 `10`，仅迭代调整激活精度，权重保持低位宽。 | 仅手册 |
| `21` | 类似 `11`，仅迭代调整激活精度。 | 仅手册 |
| `22` | 类似 `12`，仅迭代调整激活精度。 | 仅手册 |

手册说明这些混合精度设置仅在自动位宽模式下生效；不同方法对 `mp-thld` 的适用性不同。迭代分析可能耗时较长。

## 5. 模型压缩

这里的压缩开关与位宽、量化粒度是不同配置项。

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--quan-en` | `0／1` | 权重量化压缩开关。 |
| `--vlc-en` | `0／1` | 可变长编码 VLC 压缩开关。 |
| `--kmeans-en` | `0／1` | 聚类压缩开关。 |
| `--mixed-en` | `0／1` | 混合压缩开关。 |

## 6. 执行模式、核心数与内存

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--op-mode` | `<整数>` | 板端执行组织模式，CNN30 必须设置。详见下表。 |
| `--core-num` | `<整数>` | 多核切分使用的核心数。帮助注明 `690` 为 `1～4`，`538` 为 `1`。 |
| `--tcm-size` | `<整数>` | 模型可用 TCM／UBuf 容量档位，按芯片单位解释，不能直接当作 MB 数量。 |
| `--share-tcm-with-aiisp` | `0／1` | 是否与 AIISP 共用 TCM。手册说明不能与 `--op-mode 31` 同用。 |
| `--job-schd` | `0／1` | job 调度开关，帮助没有进一步解释调度算法。 |
| `--buf-thld` | `1～65535` | 用于计算图复杂度的 buffer 阈值。 |
| `--graph-thld` | `1～65535` | 用于计算图复杂度的 graph 阈值。 |
| `--mem-alloc-scheme` | `0／1／2／3` | buffer 重排策略：`0` 默认；`1` 带宽优化优先；`2` 执行时间优化优先，但帮助明确标为不支持；`3` 快速生成。 |
| `--mem-alloc-timeout` | `<整数>` | buffer 重排计算超时设置；帮助未说明时间单位。 |
| `--backend-order` | `<字符串>` | 执行后端组合，帮助列出 `CPU`、`DSP_CPU`、`EXT_DSP_CPU`。 |
| `--use-heteroge` | `0／1` | 当前帮助解释为 ACL 后端开关：`0` 关闭 ACL 后端；`1` 开启。与手册描述有差异。 |
| `--runtime-mode` | `0／1` | 工具内部推理方式：`0` 逐算子；`1` 整图。 |

### 6.1 CNN30 op-mode

| 值 | 中文说明 | 来源 |
| --- | --- | --- |
| `0` | Debug 模式，帮助描述为线性模式下调试。 | 帮助＋手册 |
| `2` | AI3 SDK 线性模式。 | 帮助＋手册 |
| `3` | AI3 SDK 图模式。 | 帮助＋手册 |
| `4` | AI3 SDK 线性模式＋UBuf／TCM。 | 帮助＋手册 |
| `5` | AI3 SDK 图模式＋UBuf／TCM。 | 帮助＋手册 |
| `6` | Transformer 网络图模式。 | 手册补充 |
| `31` | 生成 AIISP 专用模型。 | 手册补充 |

手册说明工具侧静态配置生成后，板端不能随意修改对应的 buf/job 优化设置；需要重新生成模型。

### 6.2 TCM 容量单位

| 芯片 | 每单位容量 | 帮助列出的档位 |
| --- | --- | --- |
| `690` | 1 MB | `1、2、4` |
| `538／539A／635` | 0.5 MB | `1、2、3` |

当前帮助未给出 `533` 的单位及档位，不应套用其他芯片。

手册说明 `mem-alloc-scheme 3` 的快速生成模式要求 Python 3.8 及相关模块，包含 typing、argparse、pandas、ortools、beartype；这属于该发布版本的要求。

## 7. 分块、预加载与融合优化

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--use-tiling` | `0／1／2` | `0` 无 tiling；`1` TCM non-tiling；`2` tiling。需结合 op-mode 和平台规格使用。 |
| `--preload-weight` | `0／1` | 权重预加载开关。 |
| `--stripe-lv` | `<整数>` | stripe 切分级别。当前帮助列出 `0` 原始策略、`5` 多核策略。 |
| `--stripe-perfmode` | `0／1` | MAC 并行优化：`0` 工具默认；`1` 使用 stripe performance 优化。 |
| `--c04-mode` | `0／1` | C0=4 模式，帮助针对 chip 690 说明 `0` 关闭、`1` 开启。 |
| `--preload-src` | `<整数>` | 输入／源数据预加载，帮助未列出完整取值。 |
| `--use-prein0` | `<整数>` | 同样描述为源数据预加载；帮助未明确是否与 preload-src 完全等价。 |
| `--msb-shrink-en` | `0／1` | 对 depthwise 层使用 MSB shrink 提升性能，默认 `0`。 |
| `--fusion-off` | 开关 | 关闭／拆开 ConvFusion 或 UtilFusion。 |
| `--merge-branches` | `0／1` | 横向分支合并，手册说明当前支持 convfusion 和 matmul，默认关闭。 |
| `--transposed-conv-mode` | `0～7` | 转置、数据排列和卷积组合优化的位掩码，详见下表。 |
| `--transpose-conv-fusion-mode` | `0～7` | 帮助列出的功能与上一项相同，控制源数据排列／转置卷积融合相关优化。 |
| `--conv-featmode` | `0／1` | 控制特定 feature mode 卷积是否拆融合：`0` 拆融合以启用 image mode 卷积；`1` 不拆融合。帮助标注为后续可能移除的临时选项。 |
| `--multi_core_score_ratio` | `0.5～1.5` | 帮助描述为 multi-scale mode 的 score 比例，未给出详细算法定义。 |
| `--multi_core_cmp_ratio` | `0.5～1.5` | 帮助描述为 multi-scale mode 的 CMP 比例，未给出详细算法定义。 |

转置／卷积优化位掩码：

| 值／位 | 含义 |
| --- | --- |
| `0` | 全部关闭。 |
| `0x1` | 启用 trans＋conv。 |
| `0x2` | 启用给 trans 添加 fake conv。 |
| `0x4` | 启用给 conv 添加 trans，仅 `539A`。 |
| `7` | 开启全部位。 |

以上按实际帮助翻译，不能仅凭参数名将其等同于 ONNX 的 ConvTranspose 算子。

## 8. AIISP／图像分块参数

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--weight-loc` | `0／1` | AIISP 权重位置：`0` DRAM；`1` UBuf。 |
| `--blk_size` | `<字符串>` | 分块尺寸，帮助给出两个维度范围均为 `1～65535`；手册示例为 `[256,144]`。 |
| `--overlap` | `0～65535` | 分块重叠量，帮助未明确单位和方向。 |
| `--slice_h` | `1～65535` | 切片高度参数。 |
| `--pipe_mode` | `0／1` | Pipeline 模式，帮助未进一步解释两种模式。 |

参数组合示例，仅说明格式，不代表可直接用于任意模型：

```bash
--op-mode 31 \
--blk_size '[256,144]' \
--slice_h 144 \
--weight-loc 1
```

## 9. 性能分析与排序

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--perflog-level` | `0／1` | `0` 用户级主要性能信息；`1` 增加带宽、计算量等详细信息。 |
| `--perfRankNum` | `<正整数>` | 性能报告显示排名前 N 项，手册默认 `5`。 |
| `--perflog-ranknum` | `<正整数>` | 与 perfRankNum 对应的另一名称。 |
| `--perfRankMode` | `0／1／2` | `0` 按执行时间排序；`1` 按 UT 利用率排序；`2` 分别按两者排序。 |
| `--perflog-rankmode` | `0／1／2` | 与 perfRankMode 对应的另一名称。 |

## 10. 调试与内部测试

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--dump-onnx-en` | 开关 | 导出各编译阶段的中间 ONNX，用于检查解析、量化、编译结果。 |
| `--print-mlir-opname` | 开关 | 打印 MLIR 算子名称，辅助定位解析异常或段错误。 |
| `--legal-debug` | `<整数>` | Legal 阶段调试模式，帮助未给出完整枚举。 |
| `--calib-debug` | `0／1` | `0` 关闭；`1` 开启并导出校准信息。 |
| `--runtime-debug-en` | 开关 | 开启内部 runtime 调试，导出逐层 ONNX。 |
| `--wapi-debug` | `0／1／2` | Weight API 调试：`0` 关闭；`1` 输出调试信息；`2` 额外导出 VLC 解码错误文件。 |
| `--module-test` | `0～4` | `0` 关闭；`1` parse；`2` legal；`3` parse＋legal；`4` calib。 |

## 11. Hugging Face／Transformer／大模型参数

这些参数通常不用于普通分类器、检测器转换。

| 参数 | 格式／取值 | 中文说明 |
| --- | --- | --- |
| `--use-hf` | 开关 | 启用 Hugging Face 模型转换流程。帮助描述疑似复制错误，此说明依据手册大模型章节。 |
| `--hf-method` | `<整数>` | HF 模型加载／转换方式；手册示例用 `1` 配合手动输入形状，完整枚举未给出。 |
| `--model-processor` | `<整数>` | 原始模型和 processor 的加载方式；手册示例用 `2` 表示 CausalLM 类模型，完整枚举未给出。 |
| `--decoder-num` | `<整数>` | 模型 decoder 数量。 |
| `--enc-len` | `<整数>` | 编码序列长度，帮助未给出详细约束。 |
| `--kvcache` | `<整数>` | 控制 KV cache，手册示例用 `1` 启用。 |
| `--optim-attention-mask` | 开关 | 优化 attention mask。 |

## 12. 手册列出但当前帮助未列出的参数

以下不能与实际帮助中的参数混为一谈。文档有说明，不等于已经通过当前二进制的参数解析或转换验证。

| 参数 | 手册说明 | 当前确认情况 |
| --- | --- | --- |
| `--quant-analysis` | 量化精度分析位掩码：`0` 关闭；`1` 整图；`2` 逐层；`4` 统计；`8` 箱线图；可相加，`15` 全开。 | 手册标注 CNN30，实际帮助未列出。 |
| `--llcmd-h-priority` | `0／1`，控制高优先级及精简 LLCMD；存在芯片和与 AIISP 同跑限制。 | 手册标注 CNN30，实际帮助未列出。 |
| `--job-opt` | 对应 `[performance/job_opt]`。 | 实际帮助未列出，不应视为 job-schd 的别名。 |
| `--buf-opt` | 对应 `[performance/buf_opt]`。 | 实际帮助未列出。 |
| `--aisdk` | AI1／AI2 SDK 模型选择。 | 手册仅标注 CNN25／CNN25P，不属于当前 V30 的适用参数。 |

## 13. 文档差异与适用限制

1. `bit-mode`：帮助只解释 `0～4`，手册另有 `5～7`；4 bit 模式尚未实际转换验证。
2. `4a8w-opt-mode` 默认值：帮助写 `0`，手册写 `1`。使用时应显式传值。手册一处还将 4a8w 写成 bit_mode=6，而后文和位宽表为 `7`，应按位宽表核对。
3. `op-mode`：帮助只解释 `0、2、3、4、5`，手册另有 `6、31`。
4. `mp-method`：帮助只列 `0、1、10、11、12`，手册另有 `20、21、22`。
5. `use-heteroge`：帮助与手册对 ACL 启用／禁用的表述存在差异，未经验证不应只凭名称推断行为。
6. `bit24-kernel-thld`：帮助描述为 kernel 大小比例，手册描述为带宽增幅，不能视为定义完全一致。
7. `use-hf`：实际帮助的文字疑似错误，本文采用手册大模型转换章节解释。
8. 帮助对某些内部参数没有详细枚举，本文保留这种不确定性，不虚构默认值或算法。
9. 参数名中的连字符、下划线和大小写必须保持原样，例如 `--keep_output_name`、`--blk_size`、`--slice_h`、`--perfRankNum`。

## 14. 分类／检测模型常用调用示例

以下沿用服务器现有的一种参数组合，仅说明调用结构，不能视为全部模型的通用最优参数。

```bash
cd /release_v04.01.250807.00/ai_tool/novatek/novaic/toolchain

export LD_LIBRARY_PATH="$PWD/repo/proprietary/opencv/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

./closeprefix/bin/compiler.V30 \
  --config-dir /job \
  --pattern-name . \
  --chip 690 \
  --op-mode 0 \
  --bit-mode 3
```

其中 `bit-mode 3` 表示 8 bit 权重＋16 bit 激活。

对应配置文件路径：

```text
/job/config/cnn25/gen_config.txt
```

配置中的路径项示例（只是片段，不是完整可运行配置）：

```ini
[path/model_dir] = /job/input/model
[path/ref_img_dir] = /calibration/platecolor/images
[path/ref_list_path] = /calibration/platecolor/ref_img_list.txt
[ref_data/num] = 100
[path/out_dir] = /job/output
```

编译器从 model_dir 读取 `deploy.onnx`，并在 out_dir 下生成编译结果，其中 SDK 模型文件名为 `nvt_model.bin`；具体是否附加网络名目录，以实际结果为准。

当前实际帮助没有列出用于指定上述模型、校准数据和输出目录的 `--input`、`--output` 参数。这些路径通过 gen_config 配置；前端 `onnx2novaonnx_converter.py` 的 `--input`、`--output` 属于另一个程序，不应混用。

可按任务分别维护车牌颜色、基础车型、特殊车型等配置，并在每次实验转换时生成配置副本，自动替换模型和输出路径。每个任务保留自己的校准集及预处理参数。

## 15. 查询当前安装版本的帮助

```bash
cd /release_v04.01.250807.00/ai_tool/novatek/novaic/toolchain

export LD_LIBRARY_PATH="$PWD/repo/proprietary/opencv/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

./closeprefix/bin/compiler.V30 --help
```

升级联咏工具版本后，应重新获取帮助并与对应版本手册核对，不能将本文件的参数支持范围直接套用到其他版本。