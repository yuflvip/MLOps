<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="导出为 ONNX"
    direction="rtl"
    size="440px"
    :close-on-click-modal="false"
  >
    <el-form
      :model="form"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="源任务">
        <el-input :model-value="taskName" disabled />
      </el-form-item>

      <el-form-item label="任务名称">
        <el-input v-model="form.task_name" placeholder="导出任务名称" />
      </el-form-item>

      <el-form-item label="转换参数 (JSON)">
        <el-input
          v-model="paramsJson"
          type="textarea"
          :rows="6"
          placeholder='{"opset_version": 12, "simplify": true}'
        />
      </el-form-item>

      <div class="drawer-footer">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          发起导出
        </el-button>
      </div>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createOnnxConversion } from '@/shared/api/modules/conversion'

const props = defineProps<{
  taskId: number
  taskName: string
}>()

const modelValue = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (e: 'submitted'): void }>()

const submitting = ref(false)

const form = ref({
  task_name: '',
})

const paramsJson = ref('{\n  "opset_version": 12,\n  "simplify": true\n}')

watch(modelValue, (val) => {
  if (val) {
    form.value.task_name = `${props.taskName}-onnx`
  }
})

async function handleSubmit() {
  let params: Record<string, unknown> = {}
  try {
    params = JSON.parse(paramsJson.value || '{}')
  } catch {
    ElMessage.error('参数 JSON 格式错误')
    return
  }

  submitting.value = true
  try {
    const result = await createOnnxConversion({
      parent_task_id: props.taskId,
      task_name: form.value.task_name || undefined,
      params,
    })

    if (result.warnings?.length) {
      result.warnings.forEach(w => ElMessage.warning(w))
    }

    ElMessage.success('ONNX 导出任务已创建')
    modelValue.value = false
    emit('submitted')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
</style>
