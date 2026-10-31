import { ref } from 'vue'
import { getProjectList, type ProjectItem } from '@/shared/api/modules/projects'
import { useLoading } from '@/shared/composables/useLoading'
import { usePagination } from '@/shared/composables/usePagination'

export function useProjectList() {
  const { loading, withLoadingSafe } = useLoading()
  const { page, pageSize, total, setTotal, onPageChange, onSizeChange } = usePagination(20)

  const items = ref<ProjectItem[]>([])
  const modelFilter = ref('')
  const modelTypeFilter = ref('')

  async function fetchList() {
    await withLoadingSafe(async () => {
      const data = await getProjectList({
        page: page.value,
        page_size: pageSize.value,
        keyword: modelFilter.value.trim() || undefined,
        model_type: modelTypeFilter.value || undefined,
      })
      items.value = data.items
      setTotal(data.total)
    })
  }

  function resetFilters() {
    modelFilter.value = ''
    modelTypeFilter.value = ''
    onPageChange(1)
  }

  return {
    items,
    loading,
    page,
    pageSize,
    total,
    modelFilter,
    modelTypeFilter,
    onPageChange,
    onSizeChange,
    fetchList,
    resetFilters,
  }
}
