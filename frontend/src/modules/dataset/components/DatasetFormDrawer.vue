<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="isEdit ? '编辑数据集' : '新建数据集'"
    direction="rtl"
    size="520px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="数据集名称" prop="name">
        <el-input v-model="form.name" placeholder="输入唯一数据集名称" />
      </el-form-item>

      <el-form-item label="本地绝对路径" prop="path">
        <el-input v-model="form.path" placeholder="/mnt/datasets/vehicle_cls" />
      </el-form-item>

      <el-form-item label="任务类型" prop="task_type">
        <el-select v-model="form.task_type" placeholder="请选择任务类型" clearable style="width: 100%">
          <el-option label="分类" value="classification" />
          <el-option label="检测" value="detection" />
          <el-option label="分割" value="segmentation" />
        </el-select>
      </el-form-item>

      <el-form-item label="分类类别" prop="class_names_text">
        <el-input
          v-model="form.class_names_text"
          type="textarea"
          :rows="6"
          placeholder="每行一个类别名称，例如：&#10;car&#10;bus&#10;truck"
        />
        <div class="field-tip">每行一个类别名称，提交时会自动去除首尾空格。</div>
      </el-form-item>

      <el-form-item label="描述 / 备注">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="4"
          placeholder="输入备注信息"
        />
      </el-form-item>

      <div class="drawer-footer">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '创建数据集' }}
        </el-button>
      </div>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  createDataset,
  updateDataset,
  type DatasetFormPayload,
  type DatasetItem,
} from '@/shared/api/modules/datasets'

const modelValue = defineModel<boolean>({ required: true })

const props = defineProps<{
  dataset?: DatasetItem | null
}>()

const emit = defineEmits<{
  (e: 'saved'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const isEdit = computed(() => Boolean(props.dataset))

const form = reactive({
  name: '',
  path: '',
  task_type: '',
  class_names_text: '',
  description: '',
})

function parseClassNames(value: string): string[] {
  return value
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

const rules: FormRules<typeof form> = {
  name: [
    {
      validator: (_rule, value: string, callback) => {
        if (!value.trim()) {
          callback(new Error('请输入数据集名称'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  path: [
    {
      validator: (_rule, value: string, callback) => {
        const normalized = value.trim()
        if (!normalized) {
          callback(new Error('请输入本地绝对路径'))
          return
        }
        if (!normalized.startsWith('/')) {
          callback(new Error('请输入 Linux 绝对路径，例如 /mnt/datasets/vehicle_cls'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  class_names_text: [
    {
      validator: (_rule, value: string, callback) => {
        if (parseClassNames(value).length === 0) {
          callback(new Error('请至少输入一个分类类别'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

watch(
  () => [modelValue.value, props.dataset] as const,
  ([visible, dataset]) => {
    if (!visible) return
    form.name = dataset?.name || ''
    form.path = dataset?.path || ''
    form.task_type = dataset?.task_type || ''
    form.class_names_text = dataset?.class_names?.join('\n') || ''
    form.description = dataset?.description || ''
  },
  { immediate: true },
)

function toPayload(): DatasetFormPayload {
  const classNames = parseClassNames(form.class_names_text)

  return {
    name: form.name.trim(),
    path: form.path.trim(),
    task_type: form.task_type || null,
    class_names: classNames,
    description: form.description.trim() || null,
  }
}

async function handleSubmit() {
  if (!formRef.value || submitting.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const payload = toPayload()
    if (isEdit.value && props.dataset) {
      await updateDataset(props.dataset.id, payload)
      ElMessage.success('数据集已更新')
    } else {
      await createDataset(payload)
      ElMessage.success('数据集已创建')
    }
    modelValue.value = false
    emit('saved')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.field-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
</style>
