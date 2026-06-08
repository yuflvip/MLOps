import { ref, watch } from 'vue'
import { getTrainingList } from '@/shared/api/modules/training'
import type { TrainingTaskSummary } from '@/shared/api/modules/training'
import type { PaginationParams } from '@/shared/types'
import { usePagination } from '@/shared/composables/usePagination'
import { useLoading } from '@/shared/composables/useLoading'

export function useTrainingList() {
  const { page, pageSize, total, setTotal, onPageChange, onSizeChange } = usePagination(20)
  const { loading, withLoadingSafe } = useLoading()

  const items = ref<TrainingTaskSummary[]>([])
  const statusFilter = ref('')

  async function fetchList() {
    await withLoadingSafe(async () => {
      const params: PaginationParams = {
        page: page.value,
        page_size: pageSize.value,
      }
      if (statusFilter.value) {
        params.status = statusFilter.value
      }
      const data = await getTrainingList(params)
      items.value = data.items
      setTotal(data.total)
    })
  }

  watch([page, pageSize, statusFilter], () => { fetchList() })

  return {
    items,
    loading,
    page,
    pageSize,
    total,
    statusFilter,
    onPageChange,
    onSizeChange,
    fetchList,
  }
}
