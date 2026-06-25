<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="isEdit ? '编辑运行环境' : '新建运行环境'"
    direction="rtl"
    size="560px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <div class="form-grid">
        <el-form-item label="环境标识" prop="code">
          <el-input v-model="form.code" placeholder="例如 convnext-conda-gpu" />
        </el-form-item>

        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="输入运行环境名称" />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item label="环境类型" prop="env_type">
          <el-select v-model="form.env_type" placeholder="请选择环境类型" style="width: 100%">
            <el-option label="Python" value="python" />
            <el-option label="Conda" value="conda" />
            <el-option label="Docker" value="docker" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-switch
            v-model="form.is_active"
            inline-prompt
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
      </div>

      <el-form-item label="Python 路径" prop="python_path">
        <el-input
          v-model="form.python_path"
          :disabled="form.env_type === 'docker'"
          placeholder="Python / Conda 环境必填"
        />
      </el-form-item>

      <el-form-item label="Docker 镜像" prop="docker_image">
        <el-input
          v-model="form.docker_image"
          :disabled="form.env_type !== 'docker'"
          placeholder="Docker 环境必填"
        />
      </el-form-item>

      <el-form-item label="默认工作目录">
        <el-input v-model="form.working_dir" placeholder="例如 /mnt/work/convnext" />
      </el-form-item>

      <el-form-item label="额外环境变量 JSON" prop="extra_env_text">
        <el-input
          v-model="form.extra_env_text"
          type="textarea"
          :rows="6"
          placeholder='例如 {"CUDA_VISIBLE_DEVICES":"2"}'
        />
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
          {{ isEdit ? '保存修改' : '创建运行环境' }}
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
  createRuntimeEnvironment,
  updateRuntimeEnvironment,
  type RuntimeEnvironmentFormPayload,
  type RuntimeEnvironmentItem,
} from '@/shared/api/modules/runtime-environments'

const modelValue = defineModel<boolean>({ required: true })

const props = defineProps<{
  runtimeEnvironmentItem?: RuntimeEnvironmentItem | null
}>()

const emit = defineEmits<{
  (e: 'saved'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const isEdit = computed(() => Boolean(props.runtimeEnvironmentItem))

const form = reactive({
  code: '',
  name: '',
  description: '',
  env_type: 'conda' as 'python' | 'conda' | 'docker',
  python_path: '',
  working_dir: '',
  docker_image: '',
  extra_env_text: '{}',
  is_active: true,
})

const rules: FormRules<typeof form> = {
  code: [{ required: true, message: '请输入环境标识', trigger: 'blur' }],
  name: [{ required: true, message: '请输入运行环境名称', trigger: 'blur' }],
  env_type: [{ required: true, message: '请选择环境类型', trigger: 'change' }],
  python_path: [
    {
      validator: (_rule, value: string, callback) => {
        if (form.env_type !== 'docker' && !value.trim()) {
          callback(new Error('Python / Conda 环境必须填写 Python 路径'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  docker_image: [
    {
      validator: (_rule, value: string, callback) => {
        if (form.env_type === 'docker' && !value.trim()) {
          callback(new Error('Docker 环境必须填写镜像名称'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  extra_env_text: [
    {
      validator: (_rule, value: string, callback) => {
        try {
          const parsed = JSON.parse(value || '{}')
          if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
            callback(new Error('额外环境变量必须是 JSON 对象'))
            return
          }
          const invalidValue = Object.values(parsed).some(item => typeof item !== 'string')
          if (invalidValue) {
            callback(new Error('额外环境变量的值必须全部是字符串'))
            return
          }
          callback()
        } catch {
          callback(new Error('请输入合法的 JSON'))
        }
      },
      trigger: 'blur',
    },
  ],
}

watch(
  () => [modelValue.value, props.runtimeEnvironmentItem] as const,
  ([visible, runtimeEnvironmentItem]) => {
    if (!visible) return
    form.code = runtimeEnvironmentItem?.code || ''
    form.name = runtimeEnvironmentItem?.name || ''
    form.description = runtimeEnvironmentItem?.description || ''
    form.env_type = runtimeEnvironmentItem?.env_type || 'conda'
    form.python_path = runtimeEnvironmentItem?.python_path || ''
    form.working_dir = runtimeEnvironmentItem?.working_dir || ''
    form.docker_image = runtimeEnvironmentItem?.docker_image || ''
    form.extra_env_text = JSON.stringify(runtimeEnvironmentItem?.extra_env || {}, null, 2)
    form.is_active = runtimeEnvironmentItem?.is_active ?? true
  },
  { immediate: true },
)

function toPayload(): RuntimeEnvironmentFormPayload {
  return {
    code: form.code.trim(),
    name: form.name.trim(),
    description: form.description.trim() || null,
    env_type: form.env_type,
    python_path: form.python_path.trim() || null,
    working_dir: form.working_dir.trim() || null,
    docker_image: form.docker_image.trim() || null,
    extra_env: JSON.parse(form.extra_env_text || '{}') as Record<string, string>,
    is_active: form.is_active,
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const payload = toPayload()
    if (isEdit.value && props.runtimeEnvironmentItem) {
      await updateRuntimeEnvironment(props.runtimeEnvironmentItem.id, payload)
      ElMessage.success('运行环境已更新')
    } else {
      await createRuntimeEnvironment(payload)
      ElMessage.success('运行环境已创建')
    }
    modelValue.value = false
    emit('saved')
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

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
</style>
