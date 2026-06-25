import { ref } from 'vue'
import { getDatasetList, type DatasetItem } from '@/shared/api/modules/datasets'
import { useLoading } from '@/shared/composables/useLoading'
import { usePagination } from '@/shared/composables/usePagination'

export function useDatasetList() {
  const { loading, withLoadingSafe } = useLoading()
  const { page, pageSize, total, setTotal, onPageChange, onSizeChange } = usePagination(20)

  const items = ref<DatasetItem[]>([])
  const nameFilter = ref('')
  const pathFilter = ref('')
  const taskTypeFilter = ref('')

  async function fetchList() {
    await withLoadingSafe(async () => {
      const data = await getDatasetList({
        page: page.value,
        page_size: pageSize.value,
        name: nameFilter.value || undefined,
        path: pathFilter.value || undefined,
        task_type: taskTypeFilter.value || undefined,
      })
      items.value = data.items
      setTotal(data.total)
    })
  }

  function resetFilters() {
    nameFilter.value = ''
    pathFilter.value = ''
    taskTypeFilter.value = ''
    onPageChange(1)
  }

  return {
    items,
    loading,
    page,
    pageSize,
    total,
    nameFilter,
    pathFilter,
    taskTypeFilter,
    onPageChange,
    onSizeChange,
    fetchList,
    resetFilters,
  }
}
