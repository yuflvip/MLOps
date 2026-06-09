<template>
  <el-card class="console-card">
    <template #header>
      <div class="console-header">
        <span>
          <span class="card-dot" />控制台日志
        </span>
        <div class="console-toolbar">
          <span class="text-muted" style="font-size: 12px">共 {{ total }} 条</span>
          <el-button
            size="small"
            :icon="Refresh"
            circle
            @click="loadInitial"
            :loading="loading"
          />
        </div>
      </div>
    </template>

    <div v-if="!clearmlTaskId" class="console-empty">
      该任务无 ClearML 关联，无法获取日志
    </div>

    <div v-else-if="loading && events.length === 0" style="padding: 20px; text-align: center">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
    </div>

    <div v-else-if="events.length === 0" class="console-empty">
      暂无日志
    </div>

    <div v-else>
      <div ref="logContainer" class="console-log font-mono">
        <div
          v-for="(evt, idx) in events"
          :key="idx"
          class="log-line"
          :class="'log-level-' + (evt.level || 'INFO').toLowerCase()"
        >
          <span class="log-time">{{ formatTimestamp(evt.timestamp) }}</span>
          <span class="log-level">{{ (evt.level || 'INFO').padEnd(7) }}</span>
          <span class="log-msg">{{ evt.msg }}</span>
        </div>
      </div>

      <div class="console-footer">
        <span class="text-muted" style="font-size: 12px">
          已显示 {{ events.length }} / {{ total }} 条
        </span>
        <el-button
          v-if="events.length < total"
          size="small"
          :loading="loadingMore"
          @click="loadMore"
        >
          加载更多
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loading, Refresh } from '@element-plus/icons-vue'
import { getTaskLog, type TaskLogEvent } from '@/shared/api/modules/clearml'

const props = defineProps<{
  clearmlTaskId: string | null
  taskStatus: string
}>()

const BATCH_SIZE = 500

const events = ref<TaskLogEvent[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const logContainer = ref<HTMLElement | null>(null)

async function loadInitial() {
  if (!props.clearmlTaskId) return
  loading.value = true
  try {
    const data = await getTaskLog({
      task: props.clearmlTaskId,
      batch_size: BATCH_SIZE,
      order: 'asc',
    })
    events.value = data.events || []
    total.value = data.total || 0
  } catch {
    // Error handled by API interceptor
  } finally {
    loading.value = false
  }
  // Scroll to bottom
  setTimeout(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  }, 50)
}

async function loadMore() {
  if (!props.clearmlTaskId || events.value.length === 0) return
  const lastTs = events.value[events.value.length - 1]?.timestamp
  if (lastTs == null) return

  loadingMore.value = true
  try {
    const data = await getTaskLog({
      task: props.clearmlTaskId,
      batch_size: BATCH_SIZE,
      from_timestamp: lastTs,
      order: 'asc',
    })
    const newEvents = data.events || []
    // Deduplicate (from_timestamp is inclusive in some cases)
    const existingTs = new Set(events.value.map(e => e.timestamp + '|' + e.msg))
    const fresh = newEvents.filter(e => !existingTs.has(e.timestamp + '|' + e.msg))
    events.value.push(...fresh)
    total.value = data.total || total.value
  } catch {
    // Error handled by API interceptor
  } finally {
    loadingMore.value = false
  }
}

function formatTimestamp(ts: number): string {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// Load when clearmlTaskId changes
watch(() => props.clearmlTaskId, (val) => {
  if (val) loadInitial()
}, { immediate: true })
</script>

<style scoped>
.console-card {
  margin-bottom: 16px;
}
.console-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.console-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.console-empty {
  padding: 24px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}
.console-log {
  background: #020a18;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.7;
}
.log-line {
  white-space: pre-wrap;
  word-break: break-all;
}
.log-time {
  color: var(--muted);
  margin-right: 8px;
}
.log-level {
  margin-right: 8px;
}
.log-msg {
  color: var(--txt);
}

/* Level colors */
.log-level-debug .log-level { color: #5f739c; }
.log-level-info .log-level { color: #dbe6ff; }
.log-level-warning .log-level,
.log-level-warn .log-level { color: #ffb020; }
.log-level-error .log-level { color: #ff5a6e; }
.log-level-warning .log-msg,
.log-level-warn .log-msg { color: #ffb020; }
.log-level-error .log-msg { color: #ff5a6e; }

.console-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}
</style>
