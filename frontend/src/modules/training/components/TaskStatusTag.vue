<template>
  <el-tag
    :type="tagType"
    size="small"
    effect="dark"
    :style="tagStyle"
  >
    {{ label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TASK_STATUS_MAP, TASK_STATUS_TAG_TYPE, TASK_STATUS_COLOR } from '@/shared/utils/constants'

const props = defineProps<{ status: string }>()

const label = computed(() => TASK_STATUS_MAP[props.status] || props.status)
const tagType = computed(() => TASK_STATUS_TAG_TYPE[props.status] || 'info')

const tagStyle = computed(() => {
  const color = TASK_STATUS_COLOR[props.status]
  if (!color) return {}
  return {
    backgroundColor: `${color}22`,
    color,
    borderColor: `${color}44`,
  }
})
</script>
