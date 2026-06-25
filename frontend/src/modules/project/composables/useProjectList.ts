import { ref } from 'vue'
import { getProjectList, type ProjectItem } from '@/shared/api/modules/projects'
import { useLoading } from '@/shared/composables/useLoading'
import { usePagination } from '@/shared/composables/usePagination'

export function useProjectList() {
  const { loading, withLoadingSafe } = useLoading()
  const { page, pageSize, total, setTotal, onPageChange, onSizeChange } = usePagination(20)

  const items = ref<ProjectItem[]>([])
  const projectFilter = ref('')
  const nameFilter = ref('')

  async function fetchList() {
    await withLoadingSafe(async () => {
      const data = await getProjectList({
        page: page.value,
        page_size: pageSize.value,
        project: projectFilter.value || undefined,
        name: nameFilter.value || undefined,
      })
      items.value = data.items
      setTotal(data.total)
    })
  }

  function resetFilters() {
    projectFilter.value = ''
    nameFilter.value = ''
    onPageChange(1)
  }

  return {
    items,
    loading,
    page,
    pageSize,
    total,
    projectFilter,
    nameFilter,
    onPageChange,
    onSizeChange,
    fetchList,
    resetFilters,
  }
}
