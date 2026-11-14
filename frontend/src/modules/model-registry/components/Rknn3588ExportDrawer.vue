<template>
  <el-drawer v-model="visible" title="导出瑞芯微3588" size="600px" :close-on-click-modal="false">
    <el-form label-width="140px" :disabled="submitting || loading">
      <el-form-item label="源 ONNX">{{ artifact?.relative_path }}</el-form-item>
      <el-form-item label="目标平台">RK3588</el-form-item>
      <el-form-item label="输出格式">
        <el-select v-model="form.profile">
          <el-option label="保留原始 ONNX 输出" value="generic" />
          <el-option label="YOLOv8 三尺度检测头（9 输出）" value="yolov8" />
        </el-select>
      </el-form-item>
      <el-alert v-if="form.profile === 'yolov8'" title="仅适用于标准 YOLOv8 检测模型。输出为三个尺度的框分布、类别概率和概率和；板端必须使用配套 DFL 解码和 NMS。" type="warning" :closable="false" />
      <el-form-item label="输出文件" required><el-input v-model="form.output_file" /></el-form-item>
      <el-form-item label="精度模式">
        <el-select v-model="form.precision">
          <el-option label="FP16（不量化）" value="fp16" />
          <el-option label="INT8（量化）" value="int8" />
          <el-option label="混合量化（INT8 + FP16）" value="hybrid" />
        </el-select>
      </el-form-item>
      <template v-if="form.precision !== 'fp16'">
        <el-form-item label="量化数据集" required>
          <el-select v-model="form.quantization_dataset_id" filterable placeholder="选择量化图片集">
            <el-option v-for="item in datasets" :key="item.id" :value="item.id"
              :label="`${item.name}（${item.image_count} 张）`" :disabled="item.image_count <= 0" />
          </el-select>
        </el-form-item>
        <el-form-item label="校准图片上限"><el-input-number v-model="form.max_samples" :min="0" :max="10000" :precision="0" /></el-form-item>
        <el-text type="info">按文件名顺序选取；0 表示使用全部图片。</el-text>
      </template>
      <el-form-item label="输入尺寸"><el-input v-model="form.input_shape" placeholder="自动读取；动态输入填写 name:1,3,h,w" /></el-form-item>
      <el-form-item label="预处理预设">
        <el-select v-model="preset" @change="applyPreset">
          <el-option label="自定义（按训练/部署配置填写）" value="custom" />
          <el-option label="YOLO：RGB / 255 / 补边" value="yolo" />
          <el-option label="HGNET：RGB / 均值标准差 / 直接拉伸" value="hgnet" />
          <el-option label="原始像素：不归一化" value="raw" />
        </el-select>
      </el-form-item>
      <el-form-item label="颜色顺序"><el-select v-model="form.color_order"><el-option label="RGB" value="rgb" /><el-option label="BGR" value="bgr" /></el-select></el-form-item>
      <el-form-item label="缩放方式"><el-select v-model="form.resize_mode"><el-option label="直接拉伸" value="resize" /><el-option label="等比例缩放 + 居中补边（114）" value="letterbox" /></el-select></el-form-item>
      <el-form-item label="Mean" required><el-input v-model="mean" placeholder="例如：0,0,0" /></el-form-item>
      <el-form-item label="Std" required><el-input v-model="std" placeholder="例如：255,255,255" /></el-form-item>
      <el-alert title="归一化公式：(像素值 − Mean) / Std。请与训练及板端预处理保持一致，避免重复归一化。颜色和缩放设置用于准备校准图片，板端需使用相同方式。" type="info" :closable="false" />
      <el-form-item label="覆盖同名文件"><el-switch v-model="form.overwrite" /></el-form-item>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    </el-form>
    <template #footer>
      <el-button :disabled="submitting" @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting || loading" @click="submit">开始转换</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createModelConversion, getOnnxInputMetadata, type ExpModelArtifactItem } from '@/shared/api/modules/exps'
import { getQuantizationDatasetList, type QuantizationDatasetItem } from '@/shared/api/modules/quantization-datasets'

const props = defineProps<{ expId: number; artifact?: ExpModelArtifactItem; modelFamily?: string; modelArchitecture?: string | null }>()
const visible = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (event: 'submitted'): void }>()
const submitting = ref(false)
const loading = ref(false)
const error = ref('')
const datasets = ref<QuantizationDatasetItem[]>([])
const mean = ref('')
const std = ref('')
const preset = ref('custom')
const defaults = () => ({ output_file: '', precision: 'hybrid' as 'fp16' | 'int8' | 'hybrid', input_shape: '',
  profile: 'generic' as 'generic' | 'yolov8',
  color_order: 'rgb' as 'rgb' | 'bgr', resize_mode: 'resize' as 'resize' | 'letterbox',
  max_samples: 200, quantization_dataset_id: undefined as number | undefined, overwrite: false })
const form = reactive(defaults())
function applyPreset() {
  if (preset.value === 'custom') return
  // HGNET AIPP uses (pixel - min_chn) * var_reci_chn; RKNN Std is its reciprocal.
  mean.value = preset.value === 'hgnet' ? '123.675,116.28,103.53' : '0,0,0'
  std.value = preset.value === 'hgnet' ? '58.395,57.12,57.375'
    : preset.value === 'yolo' ? '255,255,255' : '1,1,1'
  form.color_order = 'rgb'
  form.resize_mode = preset.value === 'yolo' ? 'letterbox' : 'resize'
}
let generation = 0
watch(visible, async open => {
  const current = ++generation
  if (!open) return
  const sourceName = props.artifact?.relative_path.split('/').pop()
  Object.assign(form, defaults(), {
    output_file: sourceName ? `rknn_output/${sourceName.replace(/\.onnx$/i, '_3588.rknn')}` : '',
  })
  error.value = ''; mean.value = ''; std.value = ''; datasets.value = []
  const architecture = props.modelArchitecture?.toLowerCase() || ''
  preset.value = architecture.startsWith('yolo') ? 'yolo'
    : architecture.startsWith('hgnet') ? 'hgnet' : 'custom'
  applyPreset()
  loading.value = true
  const results = await Promise.allSettled([
    getQuantizationDatasetList({ page: 1, page_size: 200 }),
    getOnnxInputMetadata(props.expId, props.artifact?.relative_path || ''),
  ])
  if (current !== generation) return
  const [data, metadata] = results
  if (data.status === 'fulfilled') {
    datasets.value = data.value.items
    form.quantization_dataset_id = datasets.value.find(item => item.image_count > 0 &&
      item.storage_path.replace(/\\/g, '/').split('/').pop() === props.modelFamily)?.id
  } else error.value = '量化数据集加载失败，可关闭后重试；FP16 不需要数据集'
  if (metadata.status === 'fulfilled') form.input_shape = metadata.value.input_shape || ''
  else error.value = '无法读取 ONNX 输入信息，请确认模型有效或填写输入尺寸'
  loading.value = false
})
function numbers(value: string) {
  const parts = value.split(',')
  if (parts.length !== 3 || parts.some(x => !x.trim() || !Number.isFinite(Number(x)))) throw new Error('Mean / Std 必须填写三个有限数值')
  return parts.map(Number)
}
async function submit() {
  if (!props.artifact || submitting.value || loading.value) return
  error.value = ''
  try {
    const output = form.output_file.trim()
    if (!output.toLowerCase().endsWith('.rknn') || output.startsWith('/') || output.includes('\\') || output.split('/').includes('..')) throw new Error('输出必须是实验目录内的 .rknn 相对路径')
    const meanValues = numbers(mean.value), stdValues = numbers(std.value)
    if (stdValues.some(x => x <= 0)) throw new Error('Std 必须大于 0')
    if (form.precision !== 'fp16' && !form.quantization_dataset_id) throw new Error('INT8 / 混合量化必须选择量化数据集')
    submitting.value = true
    try {
      await ElMessageBox.confirm(`源文件：${props.artifact.relative_path}；输出：${output}；输出格式：${form.profile === 'yolov8' ? 'YOLOv8 九输出，需配套后处理' : '保留原始结构'}；精度：${form.precision === 'hybrid' ? '混合量化（INT8 + FP16）' : form.precision.toUpperCase()}；颜色：${form.color_order.toUpperCase()}；Mean：${mean.value}；Std：${std.value}；覆盖：${form.overwrite ? '是' : '否'}`, 'RK3588 导出确认', { confirmButtonText: '开始转换', cancelButtonText: '取消' })
    } catch { return }
    const { output_file: _, quantization_dataset_id, ...params } = form
    await createModelConversion(props.expId, { converter_code: 'onnx_to_rk3588',
      source_file: props.artifact.relative_path, output_file: output,
      params: { ...params, input_shape: params.input_shape.trim(), mean: meanValues, std: stdValues,
        ...(form.precision !== 'fp16' ? { quantization_dataset_id } : {}) } })
    ElMessage.success('RK3588 转换任务已创建')
    visible.value = false
    emit('submitted')
  } catch (e) { error.value = e instanceof Error ? e.message : '创建转换任务失败' }
  finally { submitting.value = false }
}
</script>
