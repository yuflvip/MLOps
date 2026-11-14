<template>
  <el-drawer v-model="visible" title="导出联咏692" size="560px" :close-on-click-modal="false">
    <el-form label-width="155px" :disabled="submitting">
      <el-form-item label="源 ONNX">{{ artifact?.relative_path }}</el-form-item>
      <el-form-item label="量化数据">
        <span>自动使用模型族 {{ modelFamily || '未设置' }} 对应的量化目录</span>
      </el-form-item>
      <el-form-item label="输出文件" required>
        <el-input v-model="form.output_file" placeholder="692_output/best_692.bin" />
      </el-form-item>
      <el-form-item label="--chip">
        <el-input-number v-model="form.chip" :min="0" :precision="0" :step="1" />
      </el-form-item>
      <el-form-item v-for="field in selectFields" :key="field.key" :label="field.label">
        <el-select v-model="form[field.key]" style="width: 100%">
          <el-option v-for="option in field.options" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="--vlc-en">
        <el-select v-model="form.vlc_en">
          <el-option label="开启（1）" :value="1" />
          <el-option label="关闭（0）" :value="0" />
        </el-select>
      </el-form-item>
      <el-form-item label="--use-onnx"><el-switch v-model="form.use_onnx" /></el-form-item>
      <el-form-item label="覆盖同名文件"><el-switch v-model="form.overwrite" /></el-form-item>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    </el-form>
    <template #footer>
      <el-button :disabled="submitting" @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">开始转换</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createModelConversion, getExpArtifacts, type ExpModelArtifactItem } from '@/shared/api/modules/exps'

const props = defineProps<{ expId: number; artifact?: ExpModelArtifactItem; modelFamily?: string }>()
const visible = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (event: 'submitted'): void }>()
const submitting = ref(false)
const error = ref('')
const defaults = () => ({ output_file: '', chip: 690, op_mode: 2, bit_mode: 1,
  quan_scheme: 1, stripe_perfmode: 1, vlc_en: 1, use_onnx: true, overwrite: false })
const form = reactive(defaults())
const selectFields = [
  { key: 'bit_mode', label: '--bit-mode', options: [
    { value: 1, label: '1 - 8w8a' }, { value: 2, label: '2 - 16a16w' }, { value: 3, label: '3 - 8w16a' },
  ] },
  { key: 'op_mode', label: '--op-mode', options: [
    { value: 0, label: '0 - 线性调试' }, { value: 2, label: '2 - 线性模式' }, { value: 3, label: '3 - 图模式' },
  ] },
  { key: 'quan_scheme', label: '--quan-scheme', options: [
    { value: 0, label: '0 - 按张量' }, { value: 1, label: '1 - 权重按通道' },
    { value: 2, label: '2 - 权重和激活均按通道' }, { value: 3, label: '3 - 通道+SmoothQuant' },
  ] },
  { key: 'stripe_perfmode', label: '--stripe-perfmode', options: [
    { value: 0, label: '0 - 默认' }, { value: 1, label: '1 - stripe-performance 优化' },
  ] },
] as const
watch(visible, open => {
  if (!open) return
  const sourceName = props.artifact?.relative_path.split('/').pop()
  Object.assign(form, defaults(), {
    output_file: sourceName ? `692_output/${sourceName.replace(/\.onnx$/i, '_692.bin')}` : '',
  })
  error.value = ''
})
async function submit() {
  if (!props.artifact || submitting.value) return
  const rawOutput = form.output_file.trim()
  if (rawOutput.startsWith('/') || rawOutput.includes('\\') || rawOutput.split('/').includes('..')) {
    error.value = '输出文件必须是实验目录内的相对路径'; return
  }
  const output = rawOutput.split('/').filter(part => part && part !== '.').join('/')
  if (!output.endsWith('.bin')) { error.value = '输出文件必须以 .bin 结尾'; return }
  if (!Number.isInteger(form.chip) || form.chip < 0) {
    error.value = '--chip 必须为非负整数'; return
  }
  submitting.value = true
  error.value = ''
  try {
    const { output_file: _, ...params } = form
    const source = props.artifact.relative_path
    const artifacts = await getExpArtifacts(props.expId)
    const exists = artifacts.items.some(item => item.relative_path === output)
    if (exists && !params.overwrite) {
      error.value = `输出文件“${output}”已存在，请开启“覆盖同名文件”或修改输出文件名`
      return
    }
    const parameterSummary = selectFields.map(field =>
      `${field.label}：${field.options.find(option => option.value === params[field.key])?.label}`,
    ).join('；')
    try {
      await ElMessageBox.confirm(
        `确认开始转换联咏692吗？源文件：${source}；目标文件：${output}；目标文件状态：${exists ? '已存在，将覆盖' : '不存在，将新建'}；模型族：${props.modelFamily || '-'}；${parameterSummary}；--chip：${params.chip}；--vlc-en：${params.vlc_en}；--use-onnx：${params.use_onnx ? '是' : '否'}；覆盖同名文件：${params.overwrite ? '是' : '否'}`,
        '联咏692转换确认',
        { type: 'warning', confirmButtonText: '开始转换', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
    await createModelConversion(props.expId, {
      converter_code: 'onnx_to_novatek692', source_file: source,
      output_file: output, params,
    })
    ElMessage.success('联咏692转换任务已创建')
    visible.value = false
    emit('submitted')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建转换任务失败'
  } finally {
    submitting.value = false
  }
}
</script>
