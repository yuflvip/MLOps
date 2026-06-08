<template>
  <div class="json-viewer">
    <pre><code>{{ formatted }}</code></pre>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: Record<string, unknown> | unknown[] | null | undefined
}>()

const formatted = computed(() => {
  if (!props.data) return '-'
  return JSON.stringify(props.data, null, 2)
})
</script>

<style scoped>
.json-viewer {
  background: #08152e;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}
.json-viewer pre {
  margin: 0;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--txt);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
