import { ref } from 'vue'

export function useLoading() {
  const loading = ref(false)

  async function withLoading<T>(fn: () => Promise<T>): Promise<T> {
    loading.value = true
    try {
      return await fn()
    } finally {
      loading.value = false
    }
  }

  async function withLoadingSafe<T>(fn: () => Promise<T>): Promise<T | undefined> {
    try {
      return await withLoading(fn)
    } catch {
      return undefined
    }
  }

  return { loading, withLoading, withLoadingSafe }
}
