import { ref } from 'vue'
import {
  getRuntimeEnvironmentList,
  type RuntimeEnvironmentItem,
} from '@/shared/api/modules/runtime-environments'
import { useLoading } from '@/shared/composables/useLoading'
import { usePagination } from '@/shared/composables/usePagination'

export function useRuntimeEnvironmentList() {
  const { loading, withLoadingSafe } = useLoading()
  const { page, pageSize, total, setTotal, onPageChange, onSizeChange } = usePagination(20)

  const items = ref<RuntimeEnvironmentItem[]>([])
  const codeFilter = ref('')
  const nameFilter = ref('')
  const envTypeFilter = ref('')
  const isActiveFilter = ref<'all' | 'true' | 'false'>('all')

  async function fetchList() {
    await withLoadingSafe(async () => {
      const data = await getRuntimeEnvironmentList({
        page: page.value,
        page_size: pageSize.value,
        code: codeFilter.value || undefined,
        name: nameFilter.value || undefined,
        env_type: envTypeFilter.value || undefined,
        is_active:
          isActiveFilter.value === 'all'
            ? undefined
            : isActiveFilter.value === 'true',
      })
      items.value = data.items
      setTotal(data.total)
    })
  }

  function resetFilters() {
    codeFilter.value = ''
    nameFilter.value = ''
    envTypeFilter.value = ''
    isActiveFilter.value = 'all'
    onPageChange(1)
  }

  return {
    items,
    loading,
    page,
    pageSize,
    total,
    codeFilter,
    nameFilter,
    envTypeFilter,
    isActiveFilter,
    onPageChange,
    onSizeChange,
    fetchList,
    resetFilters,
  }
}
