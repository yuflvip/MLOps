<template>
  <div class="placeholder-page">
    <div class="placeholder-content">
      <h2>
        <span class="page-bar" />
        {{ title }}
      </h2>
      <p>该功能正在开发中，敬请期待。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
}>()
</script>

<style scoped>
.placeholder-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
.placeholder-content {
  text-align: center;
}
.placeholder-content h2 {
  font-size: 21px;
  font-weight: 700;
  margin-bottom: 12px;
}
.placeholder-content p {
  color: var(--muted);
  font-size: 14px;
}
</style>
