<template>
  <div class="template-list-page">
    <PageHeader title="模板管理" subtitle="浏览可用的训练模板配置" />

    <div v-loading="loading" class="template-grid">
      <template v-if="templates.length">
        <TemplateCard
          v-for="tpl in templates"
          :key="tpl.name"
          :template="tpl"
          @click="openDetail(tpl)"
        />
      </template>
      <EmptyState v-else description="暂无可用模板" />
    </div>

    <TemplateDetailDialog
      v-model="showDetail"
      :template="selectedTemplate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import EmptyState from '@/shared/components/EmptyState.vue'
import TemplateCard from './TemplateCard.vue'
import TemplateDetailDialog from './TemplateDetailDialog.vue'
import { useTemplates } from '../composables/useTemplates'
import type { TrainingCreateMetaTemplate } from '@/shared/api/modules/training'

const { templates, loading, load } = useTemplates()
const showDetail = ref(false)
const selectedTemplate = ref<TrainingCreateMetaTemplate | null>(null)

function openDetail(tpl: TrainingCreateMetaTemplate) {
  selectedTemplate.value = tpl
  showDetail.value = true
}

onMounted(() => { load() })
</script>

<style scoped>
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
</style>
