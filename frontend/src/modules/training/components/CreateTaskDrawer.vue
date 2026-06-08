<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="创建训练任务"
    direction="rtl"
    size="480px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="任务名称" prop="task_name">
        <el-input v-model="form.task_name" placeholder="输入任务名称" />
      </el-form-item>

      <el-form-item label="选择模板" prop="template_name">
        <el-select
          v-model="form.template_name"
          placeholder="请选择模板"
          style="width: 100%"
          @change="handleTemplateChange"
        >
          <el-option
            v-for="t in templates"
            :key="t.name"
            :label="t.display_name || t.name"
            :value="t.name"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="选择队列">
        <el-select
          v-model="form.queue_name"
          placeholder="请选择队列"
          style="width: 100%"
          clearable
        >
          <el-option
            v-for="q in queues"
            :key="q.queue_name"
            :label="`${q.queue_name} (${q.agent_count} agents)`"
            :value="q.queue_name"
          >
            <span>{{ q.queue_name }}</span>
            <span style="float: right; color: var(--muted); font-size: 12px">
              {{ q.agent_count }} agents
              <span v-if="!q.has_online_agents" style="color: var(--amber)"> (离线)</span>
            </span>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item v-if="selectedTemplate" label="模板参数">
        <div class="param-editor">
          <div v-for="(value, key) in form.params" :key="key" class="param-row">
            <span class="param-key">{{ key }}</span>
            <el-input
              :model-value="String(value)"
              @update:model-value="updateParam(key, $event)"
              size="small"
            />
          </div>
          <div v-if="Object.keys(form.params).length === 0" class="text-muted" style="font-size: 12px">
            该模板无默认参数
          </div>
        </div>
      </el-form-item>

      <div class="drawer-footer">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          提交任务
        </el-button>
      </div>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useTrainingStore } from '../stores/training'
import { createTraining } from '@/shared/api/modules/training'

const modelValue = defineModel<boolean>({ required: true })
const emit = defineEmits<{ (e: 'created'): void }>()

const trainingStore = useTrainingStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const templates = computed(() => trainingStore.createMeta?.templates || [])
const queues = computed(() => trainingStore.createMeta?.queues || [])

const selectedTemplate = computed(() =>
  templates.value.find(t => t.name === form.value.template_name)
)

const form = ref({
  task_name: '',
  template_name: '',
  queue_name: null as string | null,
  params: {} as Record<string, unknown>,
})

const rules: FormRules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  template_name: [{ required: true, message: '请选择模板', trigger: 'change' }],
}

watch(modelValue, (val) => {
  if (val) {
    trainingStore.loadCreateMeta()
    form.value = { task_name: '', template_name: '', queue_name: null, params: {} }
  }
})

function handleTemplateChange(name: string) {
  const tpl = templates.value.find(t => t.name === name)
  form.value.queue_name = tpl?.queue || null
  form.value.params = tpl ? { ...tpl.defaults } : {}
}

function updateParam(key: string, val: string) {
  form.value.params[key] = val
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const result = await createTraining({
      task_name: form.value.task_name,
      template_name: form.value.template_name,
      params: form.value.params,
      queue_name: form.value.queue_name,
    })

    if (result.warnings?.length) {
      result.warnings.forEach(w => ElMessage.warning(w))
    }

    ElMessage.success('训练任务已创建')
    modelValue.value = false
    emit('created')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.param-editor {
  width: 100%;
}
.param-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.param-key {
  min-width: 120px;
  font-size: 12.5px;
  color: var(--txt2);
  font-family: Consolas, monospace;
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
