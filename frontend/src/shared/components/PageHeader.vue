<template>
  <div class="page-h">
    <h2>
      <span class="page-bar" />
      {{ title }}
    </h2>
    <p v-if="subtitle">{{ subtitle }}</p>
    <div class="page-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped>
.page-h {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  margin-bottom: 16px;
}
.page-h h2 {
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 1px;
}
.page-h p {
  color: var(--txt2);
  font-size: 12.5px;
  margin-bottom: 2px;
}
.page-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
</style>
