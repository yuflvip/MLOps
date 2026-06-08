<template>
  <div class="template-card glow-card" @click="$emit('click')">
    <div class="card-header">
      <span class="card-dot" />
      <span class="card-title">{{ template.display_name || template.name }}</span>
    </div>
    <div class="card-body">
      <div class="card-row">
        <span class="label">模板编码</span>
        <span class="value font-mono">{{ template.name }}</span>
      </div>
      <div v-if="template.entrypoint" class="card-row">
        <span class="label">入口脚本</span>
        <span class="value font-mono">{{ template.entrypoint }}</span>
      </div>
      <div v-if="template.queue" class="card-row">
        <span class="label">默认队列</span>
        <span class="value">{{ template.queue }}</span>
      </div>
      <div class="card-row">
        <span class="label">默认参数</span>
        <span class="value">{{ paramCount }} 项</span>
      </div>
    </div>
    <div class="card-footer">
      <el-button link type="primary" size="small">查看详情</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TrainingCreateMetaTemplate } from '@/shared/api/modules/training'

const props = defineProps<{ template: TrainingCreateMetaTemplate }>()
defineEmits<{ (e: 'click'): void }>()

const paramCount = computed(() => Object.keys(props.template.defaults || {}).length)
</script>

<style scoped>
.template-card {
  background: linear-gradient(180deg, var(--panel), rgba(10, 22, 48, 0.6));
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
  cursor: pointer;
}
.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.card-title {
  font-size: 14px;
  font-weight: 700;
  color: #eaf1ff;
}
.card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.card-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}
.card-row .label {
  color: var(--muted);
}
.card-row .value {
  color: var(--txt2);
}
.card-footer {
  margin-top: 12px;
  text-align: right;
}
</style>
