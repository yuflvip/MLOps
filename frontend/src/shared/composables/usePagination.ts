import { reactive, computed } from 'vue'

export function usePagination(defaultPageSize = 20) {
  const state = reactive({
    page: 1,
    pageSize: defaultPageSize,
    total: 0,
  })

  const totalPages = computed(() => Math.ceil(state.total / state.pageSize) || 1)

  function onPageChange(page: number) {
    state.page = page
  }

  function onSizeChange(size: number) {
    state.pageSize = size
    state.page = 1
  }

  function reset() {
    state.page = 1
    state.total = 0
  }

  return {
    page: computed(() => state.page),
    pageSize: computed(() => state.pageSize),
    total: computed(() => state.total),
    totalPages,
    setTotal: (n: number) => { state.total = n },
    onPageChange,
    onSizeChange,
    reset,
  }
}
