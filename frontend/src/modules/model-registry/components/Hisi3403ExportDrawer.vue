<template>
  <el-drawer
    v-model="visible"
    title="导出海思3403"
    direction="rtl"
    size="600px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="right"
      label-width="230px"
      class="export-form"
    >
      <div class="form-section-title">模型与转换类型</div>
      <el-form-item label="源ONNX模型">
        <el-input :model-value="artifact?.relative_path" disabled />
      </el-form-item>
      <el-form-item label="转换类型" prop="conversion_type">
        <el-select v-model="form.conversion_type" style="width: 100%">
          <el-option label="海思 SVP_NNN（量化）" value="svp_nnn" />
          <el-option label="昇腾 NNN（非量化）" value="ascend_nnn" />
        </el-select>
      </el-form-item>
      <el-form-item
        v-if="form.conversion_type === 'svp_nnn'"
        label="量化数据集"
        prop="quantization_dataset_id"
      >
        <el-select
          v-model="form.quantization_dataset_id"
          filterable
          placeholder="请选择量化数据集"
          :loading="datasetLoading"
          style="width: 100%"
        >
          <el-option
            v-for="item in datasets"
            :key="item.id"
            :value="item.id"
            :label="`${item.name}（${item.image_count}张）`"
            :disabled="item.image_count <= 0"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="输出OM文件" prop="output_file">
        <el-input v-model="form.output_file" placeholder="例如 weights/best.om" />
      </el-form-item>

      <div class="form-section-title">转换参数</div>
      <el-form-item label="输入Shape（--input-shape）" prop="input_shape">
        <el-input
          v-model="form.input_shape"
          clearable
          placeholder="选填；自动解析失败时需填写，例如 images:1,3,640,640"
        />
      </el-form-item>
      <el-form-item label="AIPP配置（--insert-op-conf）">
        <el-select v-model="form.insert_op_conf" style="width: 100%">
          <template v-if="form.conversion_type === 'svp_nnn'">
            <el-option label="insert_op.cfg（YOLO）" value="insert_op.cfg" />
            <el-option label="insert_op_hgnet.cfg（HGNet）" value="insert_op_hgnet.cfg" />
          </template>
          <el-option
            v-else
            label="insert_op_nnn_hgnet.cfg（HGNet NNN）"
            value="insert_op_nnn_hgnet.cfg"
          />
        </el-select>
      </el-form-item>

      <div v-if="form.conversion_type === 'svp_nnn'" class="two-column">
        <el-form-item label="芯片版本（--soc-version）" prop="soc_version">
          <el-input v-model="form.soc_version" />
        </el-form-item>
        <el-form-item label="编译模式（--compile-mode）" prop="compile_mode">
          <el-input v-model="form.compile_mode" />
        </el-form-item>
        <el-form-item label="输出类型（--output-type）">
          <el-input v-model="form.output_type" clearable />
        </el-form-item>
        <el-form-item label="量化模式（--quant-mode）" prop="quant_mode">
          <el-select v-model="form.quant_mode" style="width: 100%">
            <el-option label="0（速度优先）" value="0" />
            <el-option label="1（精度优先）" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item label="在线模型类型（--online-model-type）" prop="online_model_type">
          <el-input v-model="form.online_model_type" />
        </el-form-item>
      </div>

      <el-form-item
        v-if="form.conversion_type === 'svp_nnn'"
        label="高精度层（--high-precision-layer）"
      >
        <el-input
          v-model="form.high_precision_layer"
          clearable
          placeholder="选填，例如 /model.22/Concat_5"
        />
      </el-form-item>
      <template v-else>
        <el-form-item label="芯片版本（--soc-version）" prop="soc_version">
          <el-input v-model="form.soc_version" />
        </el-form-item>
        <el-form-item label="单流模式（--enable-single-stream）">
          <el-switch v-model="form.enable_single_stream" />
        </el-form-item>
        <el-form-item label="小通道优化（--enable-small-channel）">
          <el-select v-model="form.enable_small_channel" style="width: 100%">
            <el-option label="1（启用）" :value="1" />
            <el-option label="0（禁用）" :value="0" />
          </el-select>
        </el-form-item>
      </template>
      <el-form-item>
        <el-checkbox v-model="form.dry_run">
          仅预览命令（不创建转换任务）
        </el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.overwrite">
          覆盖已存在的同名OM文件
        </el-checkbox>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ form.dry_run ? '预览命令' : '开始转换' }}
      </el-button>
    </template>
  </el-drawer>

  <el-dialog
    v-model="commandPreviewVisible"
    title="海思3403命令预览"
    width="min(960px, 90vw)"
    append-to-body
  >
    <pre class="command-preview"><code>{{ commandPreview }}</code></pre>
    <template #footer>
      <el-button type="primary" @click="commandPreviewVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import {
  createModelConversion,
  type ExpModelArtifactItem,
} from '@/shared/api/modules/exps'
import {
  getQuantizationDatasetList,
  type QuantizationDatasetItem,
} from '@/shared/api/modules/quantization-datasets'

const props = defineProps<{
  expId: number
  artifact?: ExpModelArtifactItem
  modelArchitecture?: string | null
  imageSize?: number | null
  expRoot: string
}>()

const visible = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (event: 'submitted'): void }>()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const datasetLoading = ref(false)
const datasets = ref<QuantizationDatasetItem[]>([])
const commandPreviewVisible = ref(false)
const commandPreview = ref('')
const form = reactive({
  conversion_type: 'svp_nnn' as 'svp_nnn' | 'ascend_nnn',
  output_file: '',
  quantization_dataset_id: undefined as number | undefined,
  input_shape: '',
  insert_op_conf: 'insert_op.cfg' as
    | 'insert_op.cfg'
    | 'insert_op_hgnet.cfg'
    | 'insert_op_nnn_hgnet.cfg',
  soc_version: 'SS928V100',
  compile_mode: '6',
  output_type: 'FP32',
  quant_mode: '1',
  high_precision_layer: '',
  online_model_type: '0',
  enable_single_stream: true,
  enable_small_channel: 1 as 0 | 1,
  dry_run: false,
  overwrite: true,
})

const rules: FormRules<typeof form> = {
  conversion_type: [
    { required: true, message: '请选择转换类型', trigger: 'change' },
  ],
  quantization_dataset_id: [
    {
      validator: (_rule, value, callback) => {
        if (form.conversion_type === 'svp_nnn' && value == null) {
          callback(new Error('请选择量化数据集'))
          return
        }
        callback()
      },
      trigger: 'change',
    },
  ],
  output_file: [
    { required: true, message: '请输入输出文件', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value.startsWith('/') || !value.toLowerCase().endsWith('.om')) {
          callback(new Error('请输入实验目录内的 .om 相对路径'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  input_shape: [
    {
      validator: (_rule, value: string, callback) => {
        if (form.conversion_type === 'ascend_nnn' && !value.trim()) {
          callback(new Error('昇腾 NNN 必须填写输入Shape'))
          return
        }
        if (value && !/^[^:,\s]+:\d+,\d+,\d+,\d+$/.test(value.trim())) {
          callback(new Error('格式应为 input_name:n,c,h,w'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  soc_version: [{ required: true, message: '请输入芯片版本', trigger: 'blur' }],
  compile_mode: [{ required: true, message: '请输入编译模式', trigger: 'blur' }],
  quant_mode: [{ required: true, message: '请选择量化模式', trigger: 'change' }],
  online_model_type: [
    { required: true, message: '请输入在线模型类型', trigger: 'blur' },
  ],
}

watch(visible, async (value) => {
  if (!value || !props.artifact) return
  resetForm()
  datasetLoading.value = true
  try {
    const data = await getQuantizationDatasetList({ page: 1, page_size: 200 })
    datasets.value = data.items
    if (datasets.value.length === 1 && datasets.value[0].image_count > 0) {
      form.quantization_dataset_id = datasets.value[0].id
    }
  } finally {
    datasetLoading.value = false
  }
})

function resetForm() {
  form.conversion_type = 'svp_nnn'
  form.output_file = props.artifact?.relative_path.replace(/\.onnx$/i, '.om') || ''
  form.quantization_dataset_id = undefined
  form.input_shape = props.imageSize
    ? `images:1,3,${props.imageSize},${props.imageSize}`
    : ''
  form.insert_op_conf = props.modelArchitecture?.toLowerCase().includes('hgnet')
    ? 'insert_op_hgnet.cfg'
    : 'insert_op.cfg'
  form.soc_version = 'SS928V100'
  form.compile_mode = '6'
  form.output_type = 'FP32'
  form.quant_mode = '1'
  form.high_precision_layer = ''
  form.online_model_type = '0'
  form.enable_single_stream = true
  form.enable_small_channel = 1
  form.dry_run = false
  form.overwrite = true
  formRef.value?.clearValidate()
}

watch(
  () => form.conversion_type,
  type => {
    if (type === 'ascend_nnn') {
      const modelName = props.artifact?.name.replace(/\.onnx$/i, '.om') || 'model.om'
      form.output_file = `hisi_atc_output_nnn/${modelName}`
      form.insert_op_conf = 'insert_op_nnn_hgnet.cfg'
      form.soc_version = 'OPTG'
      form.quantization_dataset_id = undefined
    } else {
      form.output_file = props.artifact?.relative_path.replace(/\.onnx$/i, '.om') || ''
      form.insert_op_conf = props.modelArchitecture?.toLowerCase().includes('hgnet')
        ? 'insert_op_hgnet.cfg'
        : 'insert_op.cfg'
      form.soc_version = 'SS928V100'
    }
    formRef.value?.clearValidate()
  },
)

async function handleSubmit() {
  if (!props.artifact || !formRef.value) return
  await formRef.value.validate()
  if (
    form.conversion_type === 'svp_nnn'
    && form.quantization_dataset_id == null
  ) return
  if (form.dry_run) {
    commandPreview.value = buildCommandPreview()
    commandPreviewVisible.value = true
    return
  }
  const dataset = datasets.value.find(
    item => item.id === form.quantization_dataset_id,
  )
  const typeLabel = form.conversion_type === 'svp_nnn'
    ? '海思 SVP_NNN（量化）'
    : '昇腾 NNN（非量化）'
  try {
    await ElMessageBox.confirm(
      `确认开始转换海思3403吗？转换类型：${typeLabel}；源文件：${props.artifact.relative_path}；目标文件：${form.output_file.trim()}；量化数据集：${form.conversion_type === 'svp_nnn' ? dataset?.name || '-' : '不需要'}；覆盖同名文件：${form.overwrite ? '是' : '否'}`,
      '海思3403转换确认',
      {
        type: 'warning',
        confirmButtonText: '开始转换',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  submitting.value = true
  try {
    if (form.conversion_type === 'svp_nnn') {
      await createModelConversion(props.expId, {
        converter_code: 'onnx_to_hisi3403',
        source_file: props.artifact.relative_path,
        output_file: form.output_file.trim(),
        params: {
          quantization_dataset_id: form.quantization_dataset_id!,
          input_shape: form.input_shape.trim(),
          insert_op_conf: form.insert_op_conf as 'insert_op.cfg' | 'insert_op_hgnet.cfg',
          soc_version: form.soc_version.trim(),
          compile_mode: form.compile_mode.trim(),
          output_type: form.output_type.trim(),
          quant_mode: form.quant_mode,
          high_precision_layer: form.high_precision_layer.trim(),
          online_model_type: form.online_model_type.trim(),
          dry_run: false,
          overwrite: form.overwrite,
        },
      })
    } else {
      await createModelConversion(props.expId, {
        converter_code: 'onnx_to_hisi3403_ascend_nnn',
        source_file: props.artifact.relative_path,
        output_file: form.output_file.trim(),
        params: {
          input_shape: form.input_shape.trim(),
          insert_op_conf: 'insert_op_nnn_hgnet.cfg',
          soc_version: form.soc_version.trim(),
          enable_single_stream: form.enable_single_stream,
          enable_small_channel: form.enable_small_channel,
          dry_run: false,
          overwrite: form.overwrite,
        },
      })
    }
    ElMessage.success('海思3403转换任务已创建')
    visible.value = false
    emit('submitted')
  } finally {
    submitting.value = false
  }
}

function shellQuote(value: string) {
  return `'${value.replace(/'/g, `'\\''`)}'`
}

function buildCommandPreview() {
  const dataset = datasets.value.find(
    item => item.id === form.quantization_dataset_id,
  )
  const expRoot = props.expRoot.replace(/\/+$/, '')
  const sourcePath = `${expRoot}/${props.artifact?.relative_path || ''}`
  const outputPath = `${expRoot}/${form.output_file.trim()}`.replace(/\.om$/i, '')
  const isSvp = form.conversion_type === 'svp_nnn'
  const scriptRoot = isSvp
    ? 'backend/scripts/model_conversion/hisi3403/svp_nnn'
    : 'backend/scripts/model_conversion/hisi3403/ascend_nnn'
  if (!isSvp) {
    const atcArgs = [
      '--framework=5',
      `--model=${shellQuote(sourcePath)}`,
      `--input_shape=${shellQuote(form.input_shape.trim())}`,
      `--insert_op_conf=${shellQuote(`${scriptRoot}/configs/${form.insert_op_conf}`)}`,
      `--output=${shellQuote(outputPath)}`,
      `--enable_single_stream=${String(form.enable_single_stream)}`,
      `--enable_small_channel=${String(form.enable_small_channel)}`,
      `--soc_version=${shellQuote(form.soc_version.trim())}`,
    ]
    return [
      'source /root/miniconda3/etc/profile.d/conda.sh',
      'conda activate ascend-env',
      'source /usr/local/Ascend/ascend-toolkit/latest/x86_64-linux/bin/setenv.bash',
      'export NPU_INCLUDE_PATH=/usr/local/Ascend/ascend-toolkit/latest/acllib/include/acl',
      'export NPU_LIB_PATH=/usr/local/Ascend/ascend-toolkit/latest/acllib/lib64/stub',
      '',
      'atc \\',
      ...atcArgs.map((arg, index) => (
        `  ${arg}${index < atcArgs.length - 1 ? ' \\' : ''}`
      )),
    ].join('\n')
  }
  const args = [
    '/usr/bin/bash',
    `${scriptRoot}/${isSvp ? 'export_svpnnn_om.sh' : 'export_nnn_om.sh'}`,
    '--model',
    sourcePath,
  ]
  if (isSvp) {
    args.push('--image-list', dataset?.image_list_path || '')
  }
  args.push(
    '--insert-op-conf',
    `${scriptRoot}/configs/${form.insert_op_conf}`,
    '--output',
    outputPath,
    '--soc-version',
    form.soc_version.trim(),
  )
  if (isSvp) {
    args.push(
      '--compile-mode', form.compile_mode.trim(),
      '--output-type', form.output_type.trim(),
      '--quant-mode', form.quant_mode,
      '--online-model-type', form.online_model_type.trim(),
    )
  } else {
    args.push(
      '--enable-single-stream', String(form.enable_single_stream),
      '--enable-small-channel', String(form.enable_small_channel),
    )
  }
  if (form.input_shape.trim()) {
    args.push('--input-shape', form.input_shape.trim())
  }
  if (form.high_precision_layer.trim()) {
    args.push('--high-precision-layer', form.high_precision_layer.trim())
  }
  const lines: string[] = []
  for (let index = 0; index < args.length; index += 2) {
    if (index === 0) {
      lines.push(`${shellQuote(args[0])} ${shellQuote(args[1])} \\`)
      continue
    }
    const suffix = index + 2 < args.length ? ' \\' : ''
    lines.push(`  ${args[index]} ${shellQuote(args[index + 1])}${suffix}`)
  }
  return lines.join('\n')
}
</script>

<style scoped>
.form-section-title {
  margin: 4px 0 14px;
  padding-left: 9px;
  border-left: 3px solid var(--cyan);
  color: var(--txt);
  font-weight: 600;
}
:deep(.export-form .el-form-item__content > .el-input),
:deep(.export-form .el-form-item__content > .el-select) {
  width: 100%;
}

.two-column {
  display: block;
}

.command-preview {
  min-height: 280px;
  max-height: 65vh;
  margin: 0;
  padding: 16px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #071127;
  color: var(--txt);
  font-size: 12.5px;
  line-height: 1.7;
  white-space: pre-wrap;
}

@media (max-width: 700px) {
  :deep(.export-form .el-form-item) {
    display: block;
  }
  :deep(.export-form .el-form-item__label) {
    display: block;
    width: 100% !important;
    height: auto;
    margin-bottom: 6px;
    text-align: left;
  }
  :deep(.export-form .el-form-item__content) {
    margin-left: 0 !important;
  }
}
</style>
