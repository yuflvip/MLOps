<template>
  <el-drawer
    v-model="visible"
    title="导出 ONNX"
    direction="rtl"
    size="460px"
    :close-on-click-modal="false"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="源模型文件">
        <el-input :model-value="artifact?.relative_path" disabled />
      </el-form-item>
      <el-form-item label="输出文件" prop="output_file">
        <el-input v-model="form.output_file" placeholder="例如 weights/best.onnx" />
      </el-form-item>
      <el-form-item label="执行设备">
        <el-select v-model="form.device" style="width: 100%">
          <el-option label="CPU" value="cpu" />
          <el-option label="CUDA" value="cuda" />
        </el-select>
      </el-form-item>
      <el-form-item label="输入尺寸" prop="imgsz">
        <el-input v-model="form.imgsz" placeholder="224 或 256,384" />
      </el-form-item>
      <el-form-item label="ONNX Opset">
        <el-input-number v-model="form.opset" :min="7" :max="21" style="width: 100%" />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.simplify">简化模型（simplify）</el-checkbox>
      </el-form-item>
      <el-form-item>
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
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  createModelConversion,
  type ExpArtifactItem,
} from '@/shared/api/modules/exps'

const props = defineProps<{
  expId: number
  artifact?: ExpArtifactItem
}>()

const visible = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (event: 'submitted'): void }>()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({
  output_file: '',
  device: 'cpu' as 'cpu' | 'cuda',
  imgsz: '224',
  opset: 13,
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
  form.imgsz = '224'
  form.opset = 13
  form.simplify = false
  form.dynamo = false
  form.overwrite = true
})

async function handleSubmit() {
  if (!props.artifact || !formRef.value) return
  await formRef.value.validate()
  submitting.value = true
  try {
    await createModelConversion(props.expId, {
      converter_code: 'hgnet_to_onnx',
      source_file: props.artifact.relative_path,
      output_file: form.output_file.trim(),
      params: {
        device: form.device,
        imgsz: form.imgsz.trim(),
        opset: form.opset,
        simplify: form.simplify,
        dynamo: form.dynamo,
        overwrite: form.overwrite,
      },
    })
    ElMessage.success('ONNX 导出任务已创建')
    visible.value = false
    emit('submitted')
  } finally {
    submitting.value = false
  }
}
</script>
