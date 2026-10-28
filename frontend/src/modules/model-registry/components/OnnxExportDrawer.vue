<template>
  <el-drawer
    v-model="visible"
    title="导出 ONNX"
    direction="rtl"
    size="540px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="right"
      label-width="150px"
      class="export-form"
    >
      <el-form-item label="源模型文件">
        <el-input :model-value="artifact?.relative_path" disabled />
      </el-form-item>
      <el-form-item label="输出文件" prop="output_file">
        <el-input v-model="form.output_file" placeholder="例如 weights/best.onnx" />
      </el-form-item>
      <el-form-item v-if="!isYolo" label="执行设备">
        <el-select v-model="form.device" style="width: 100%">
          <el-option label="CPU" value="cpu" />
          <el-option label="CUDA" value="cuda" />
        </el-select>
      </el-form-item>
      <el-form-item label="输入尺寸" prop="imgsz">
        <el-input v-model="form.imgsz" placeholder="224 或 256,384" />
      </el-form-item>
      <el-form-item label="ONNX Opset">
        <el-input-number
          v-model="form.opset"
          :min="7"
          :max="21"
          clearable
          placeholder="留空使用默认值"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item v-if="isYolo">
        <el-checkbox v-model="form.end2end">启用 end2end</el-checkbox>
      </el-form-item>
      <el-form-item v-if="!isYolo">
        <el-checkbox v-model="form.simplify">简化模型（simplify）</el-checkbox>
      </el-form-item>
      <el-form-item v-if="!isYolo">
        <el-checkbox v-model="form.dynamo">使用 Dynamo 导出器</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.overwrite">覆盖已存在的同名 ONNX 文件</el-checkbox>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        开始导出
      </el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import {
  createModelConversion,
  type ExpArtifactItem,
} from '@/shared/api/modules/exps'

const props = defineProps<{
  expId: number
  artifact?: ExpArtifactItem
  modelArchitecture?: string | null
}>()

const visible = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (event: 'submitted'): void }>()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const isYolo = computed(() => ['YOLOv8', 'YOLOv26'].includes(props.modelArchitecture || ''))
const form = reactive({
  output_file: '',
  device: 'cpu' as 'cpu' | 'cuda',
  imgsz: '224',
  opset: 13 as number | undefined,
  end2end: false,
  simplify: false,
  dynamo: false,
  overwrite: true,
})

const rules: FormRules<typeof form> = {
  output_file: [
    { required: true, message: '请输入输出文件', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value.startsWith('/') || !value.toLowerCase().endsWith('.onnx')) {
          callback(new Error('请输入实验目录内的 .onnx 相对路径'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  imgsz: [
    { required: true, message: '请输入输入尺寸', trigger: 'blur' },
    {
      pattern: /^\d+(,\d+)?$/,
      message: '请输入正整数或 高,宽，例如 224 或 256,384',
      trigger: 'blur',
    },
  ],
}

watch(visible, (value) => {
  if (!value || !props.artifact) return
  form.output_file = props.artifact.relative_path.replace(/\.(pt|pth)$/i, '.onnx')
  form.device = 'cpu'
  form.imgsz = isYolo.value ? '640' : '224'
  form.opset = isYolo.value ? undefined : 13
  form.end2end = false
  form.simplify = false
  form.dynamo = false
  form.overwrite = true
})

async function handleSubmit() {
  if (!props.artifact || !formRef.value) return
  await formRef.value.validate()
  try {
    await ElMessageBox.confirm(
      `确认开始导出ONNX吗？源文件：${props.artifact.relative_path}；目标文件：${form.output_file.trim()}；覆盖同名文件：${form.overwrite ? '是' : '否'}`,
      '导出ONNX确认',
      {
        type: 'warning',
        confirmButtonText: '开始导出',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  submitting.value = true
  try {
    const params = isYolo.value
      ? {
          imgsz: form.imgsz.trim(),
          end2end: form.end2end,
          ...(form.opset == null ? {} : { opset: form.opset }),
          overwrite: form.overwrite,
        }
      : {
          device: form.device,
          imgsz: form.imgsz.trim(),
          opset: form.opset ?? 13,
          simplify: form.simplify,
          dynamo: form.dynamo,
          overwrite: form.overwrite,
        }
    await createModelConversion(props.expId, {
      converter_code: isYolo.value ? 'yolo_to_onnx' : 'hgnet_to_onnx',
      source_file: props.artifact.relative_path,
      output_file: form.output_file.trim(),
      params,
    })
    ElMessage.success('ONNX 导出任务已创建')
    visible.value = false
    emit('submitted')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
:deep(.export-form .el-form-item__content > .el-input),
:deep(.export-form .el-form-item__content > .el-select),
:deep(.export-form .el-form-item__content > .el-input-number) {
  width: 100%;
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
