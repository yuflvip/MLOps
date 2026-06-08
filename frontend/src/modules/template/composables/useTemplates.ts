import { computed } from 'vue'
import { useTemplateStore } from '../stores/template'

export function useTemplates() {
  const store = useTemplateStore()

  const templates = computed(() => store.data?.templates || [])
  const loading = computed(() => store.loading)

  function load() {
    store.loadTemplates()
  }

  return { templates, loading, load }
}
