<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="`模板详情: ${template?.display_name || template?.name || ''}`"
    width="680px"
    destroy-on-close
  >
    <template v-if="template">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="模板名称">{{ template.name }}</el-descriptions-item>
        <el-descriptions-item label="显示名称">{{ template.display_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="默认队列">{{ template.queue || '-' }}</el-descriptions-item>
        <el-descriptions-item label="入口脚本">{{ template.entrypoint || '-' }}</el-descriptions-item>
      </el-descriptions>

      <h4 v-if="template.runtime" style="margin: 16px 0 8px; color: var(--txt)">运行时配置</h4>
      <el-descriptions v-if="template.runtime" :column="2" border>
        <el-descriptions-item label="启动器">{{ template.runtime.launcher }}</el-descriptions-item>
        <el-descriptions-item label="工作目录">{{ template.runtime.working_dir || '-' }}</el-descriptions-item>
        <el-descriptions-item label="脚本路径" :span="2">{{ template.runtime.script_path || '-' }}</el-descriptions-item>
      </el-descriptions>

      <h4 v-if="template.runtime?.artifacts?.length" style="margin: 16px 0 8px; color: var(--txt)">产物配置</h4>
      <el-table v-if="template.runtime?.artifacts?.length" :data="template.runtime.artifacts" size="small" stripe>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="role" label="角色" />
        <el-table-column prop="format" label="格式" />
        <el-table-column prop="path" label="路径" show-overflow-tooltip />
      </el-table>

      <h4 style="margin: 16px 0 8px; color: var(--txt)">默认参数</h4>
      <JsonViewer :data="template.defaults" />
    </template>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
      <el-button type="primary" @click="handleUseTemplate">
        使用此模板创建任务
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import JsonViewer from '@/shared/components/JsonViewer.vue'
import type { TrainingCreateMetaTemplate } from '@/shared/api/modules/training'

const props = defineProps<{
  template: TrainingCreateMetaTemplate | null
}>()

const modelValue = defineModel<boolean>({ required: true })

const router = useRouter()

function handleUseTemplate() {
  if (props.template) {
    modelValue.value = false
    router.push({ path: '/training', query: { template: props.template.name } })
  }
}
</script>
