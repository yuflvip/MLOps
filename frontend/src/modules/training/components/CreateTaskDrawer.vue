<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="创建训练任务"
    direction="rtl"
    size="480px"
  >
    <p>CreateTaskDrawer stub — will be implemented in Task 9</p>
  </el-drawer>
</template>

<script setup lang="ts">
const modelValue = defineModel<boolean>({ required: true })
defineEmits<{ (e: 'created'): void }>()
</script>
