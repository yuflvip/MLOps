<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="isEdit ? '编辑模型族' : '新建模型族'"
    direction="rtl"
    size="min(760px, 100vw)"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <div class="two-column-grid">
      <el-form-item label="模型族标识" prop="project">
        <el-input v-model="form.project" placeholder="输入唯一模型族标识" />
      </el-form-item>

      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="输入模型族名称" />
      </el-form-item>

      </div>

      <div class="two-column-grid">
      <el-form-item label="模型类型" prop="model_type">
        <el-select v-model="form.model_type" placeholder="请选择模型类型" style="width: 100%">
          <el-option label="分类器" value="classification" />
          <el-option label="检测器" value="detection" />
          <el-option label="轮廓分割" value="segmentation" />
        </el-select>
      </el-form-item>

      <el-form-item label="模型架构" prop="model_architecture">
        <el-select
          v-model="form.model_architecture"
          placeholder="请选择模型架构"
          style="width: 100%"
        >
          <el-option
            v-for="architecture in architectureOptions"
            :key="architecture"
            :label="architecture"
            :value="architecture"
          />
        </el-select>
      </el-form-item>

      </div>

      <el-form-item label="实验根路径" prop="exp_root_path">
        <el-input
          v-model="form.exp_root_path"
          placeholder="例如 /mnt/training-results/vehicle-color"
        />
      </el-form-item>

      <el-form-item label="绑定数据集" prop="dataset_ids">
        <el-select
          v-model="form.dataset_ids"
          multiple
          filterable
          placeholder="请选择要绑定的数据集"
          style="width: 100%"
        >
          <el-option
            v-for="dataset in datasetOptions"
            :key="dataset.id"
            :label="dataset.name"
            :value="dataset.id"
          />
        </el-select>
      </el-form-item>

      <div class="param-grid">
        <el-form-item label="epochs">
          <el-input-number v-model="form.epochs" :min="1" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="batch">
          <el-input-number v-model="form.batch" :min="1" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="imgsz">
          <el-input-number v-model="form.imgsz" :min="1" controls-position="right" style="width: 100%" />
        </el-form-item>
      </div>

      <ProjectPackagingEditor v-model="form.packaging" :project-key="form.project" section="links" />

      <ProjectPackagingEditor v-model="form.packaging" :project-key="form.project" section="files" />

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
          {{ isEdit ? '保存修改' : '创建模型族' }}
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
  createProject,
  updateProject,
  type ProjectFormPayload,
  type ProjectItem,
} from '@/shared/api/modules/projects'
import ProjectPackagingEditor from './ProjectPackagingEditor.vue'
import { emptyPackaging } from '@/shared/api/modules/projects'
import type { DatasetItem } from '@/shared/api/modules/datasets'

const modelValue = defineModel<boolean>({ required: true })

const props = defineProps<{
  projectItem?: ProjectItem | null
  datasets: DatasetItem[]
}>()

const emit = defineEmits<{
  (e: 'saved'): void
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const isEdit = computed(() => Boolean(props.projectItem))
const datasetOptions = computed(() => props.datasets)
const architectureOptions = computed(() => {
  if (form.model_type === 'classification') return ['HGNetV2', 'EC', 'unknown']
  if (form.model_type === 'detection') return ['YOLOv26', 'YOLOv8', 'unknown']
  return ['unknown']
})

const form = reactive({
  packaging: emptyPackaging(),
  project: '',
  name: '',
  model_type: '',
  model_architecture: 'unknown',
  description: '',
  exp_root_path: '',
  dataset_ids: [] as number[],
  epochs: undefined as number | undefined,
  batch: undefined as number | undefined,
  imgsz: undefined as number | undefined,
})

const rules: FormRules<typeof form> = {
  project: [{ required: true, message: '请输入模型族标识', trigger: 'blur' }],
  name: [{ required: true, message: '请输入模型族名称', trigger: 'blur' }],
  model_type: [{ required: true, message: '请选择模型类型', trigger: 'change' }],
  model_architecture: [{ required: true, message: '请选择模型架构', trigger: 'change' }],
  exp_root_path: [
    { required: true, message: '请输入实验根路径', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value.trim() && !value.trim().startsWith('/')) {
          callback(new Error('实验根路径必须是绝对路径'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  dataset_ids: [{ required: true, message: '请选择至少一个数据集', trigger: 'change' }],
}

watch(
  () => [modelValue.value, props.projectItem] as const,
  ([visible, projectItem]) => {
    if (!visible) return
    form.packaging = { ...emptyPackaging(), ...projectItem?.packaging, model_links: { ...projectItem?.packaging?.model_links } }
    form.project = projectItem?.project || ''
    form.name = projectItem?.name || ''
    form.model_type = projectItem?.model_type || ''
    form.model_architecture = projectItem?.model_architecture || 'unknown'
    form.description = projectItem?.description || ''
    form.exp_root_path = projectItem?.exp_root_path || ''
    form.dataset_ids = projectItem?.dataset_ids ? [...projectItem.dataset_ids] : []
    form.epochs = projectItem?.epochs ?? undefined
    form.batch = projectItem?.batch ?? undefined
    form.imgsz = projectItem?.imgsz ?? undefined
  },
  { immediate: true },
)

watch(
  () => form.model_type,
  () => {
    if (!architectureOptions.value.includes(form.model_architecture)) {
      form.model_architecture = 'unknown'
    }
  },
)

function toPayload(): ProjectFormPayload {
  return {
    packaging: JSON.parse(JSON.stringify(form.packaging)),
    project: form.project.trim(),
    name: form.name.trim(),
    model_type: form.model_type,
    model_architecture: form.model_architecture,
    description: form.description.trim() || null,
    exp_root_path: form.exp_root_path.trim(),
    dataset_ids: [...form.dataset_ids],
    epochs: form.epochs ?? null,
    batch: form.batch ?? null,
    imgsz: form.imgsz ?? null,
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    const payload = toPayload()
    if (isEdit.value && props.projectItem) {
      await updateProject(props.projectItem.id, payload)
      ElMessage.success('模型族已更新')
    } else {
      await createProject(payload)
      ElMessage.success('模型族已创建')
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

.two-column-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.param-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
</style>
