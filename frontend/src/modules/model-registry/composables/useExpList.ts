import { ref } from 'vue'
import { getExpList, type ExpItem, type ExpReviewStatus } from '@/shared/api/modules/exps'
import { useLoading } from '@/shared/composables/useLoading'
import { usePagination } from '@/shared/composables/usePagination'

export function useExpList() {
  const { loading, withLoadingSafe } = useLoading()
  const { page, pageSize, total, setTotal, onPageChange, onSizeChange } = usePagination(20)
  const items = ref<ExpItem[]>([])
  const projectIdFilter = ref<number | undefined>()
  const statusFilter = ref<ExpReviewStatus | undefined>()

  async function fetchList() {
    await withLoadingSafe(async () => {
      const data = await getExpList({
        page: page.value,
        page_size: pageSize.value,
        project_id: projectIdFilter.value,
        review_status: statusFilter.value,
      })
      items.value = data.items
      setTotal(data.total)
    })
  }

  function resetFilters() {
    projectIdFilter.value = undefined
    statusFilter.value = undefined
    onPageChange(1)
  }

  return {
    items,
    loading,
    page,
    pageSize,
    total,
    projectIdFilter,
    statusFilter,
    onPageChange,
    onSizeChange,
    fetchList,
    resetFilters,
  }
}
