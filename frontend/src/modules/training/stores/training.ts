import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TrainingCreateMetaData } from '@/shared/api/modules/training'
import { getTrainingCreateMeta } from '@/shared/api/modules/training'

export const useTrainingStore = defineStore('training', () => {
  const createMeta = ref<TrainingCreateMetaData | null>(null)
  const createMetaLoading = ref(false)

  async function loadCreateMeta() {
    createMetaLoading.value = true
    try {
      createMeta.value = await getTrainingCreateMeta()
    } finally {
      createMetaLoading.value = false
    }
  }

  return { createMeta, createMetaLoading, loadCreateMeta }
})
