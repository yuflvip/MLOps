import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TrainingCreateMetaData } from '@/shared/api/modules/training'
import { getTrainingCreateMeta } from '@/shared/api/modules/training'

export const useTemplateStore = defineStore('template', () => {
  const data = ref<TrainingCreateMetaData | null>(null)
  const loading = ref(false)

  async function loadTemplates() {
    if (data.value) return
    loading.value = true
    try {
      data.value = await getTrainingCreateMeta()
    } finally {
      loading.value = false
    }
  }

  return { data, loading, loadTemplates }
})
