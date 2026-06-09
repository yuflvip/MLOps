<template>
  <div class="task-detail-page">
    <div class="detail-header">
      <el-button link @click="router.push('/training')">
        ← 返回列表
      </el-button>
      <h2 style="margin-left: 12px">{{ task?.task_name || '加载中...' }}</h2>
    </div>

    <div v-if="loading" style="padding: 40px; text-align: center">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <template v-else-if="task">
      <!-- Basic Info -->
      <el-card class="detail-card">
        <template #header>
          <span class="card-dot" />基本信息
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务名称">{{ task.task_name }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">{{ task.task_type }}</el-descriptions-item>
          <el-descriptions-item label="模板">{{ task.template_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <TaskStatusTag :status="task.status" />
          </el-descriptions-item>
          <el-descriptions-item label="队列">{{ task.queue_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ task.task_source }}</el-descriptions-item>
          <el-descriptions-item label="ClearML ID">
            <span class="font-mono">{{ task.clearml_task_id || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            <span class="font-mono">{{ formatTime(task.created_at) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            <span class="font-mono">{{ formatTime(task.updated_at) }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="task.error_message" label="错误信息">
            <span style="color: var(--red)">{{ task.error_message }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- Parameter Snapshot -->
      <el-card v-if="task.parameter_snapshot && Object.keys(task.parameter_snapshot).length" class="detail-card">
        <template #header>
          <span class="card-dot" />参数快照
        </template>
        <JsonViewer :data="task.parameter_snapshot" />
      </el-card>

      <!-- Runtime Snapshot -->
      <el-card v-if="task.runtime_snapshot && Object.keys(task.runtime_snapshot).length" class="detail-card">
        <template #header>
          <span class="card-dot" />运行时信息
        </template>
        <JsonViewer :data="task.runtime_snapshot" />
      </el-card>

      <!-- Result Summary -->
      <el-card v-if="task.result_summary && Object.keys(task.result_summary).length" class="detail-card">
        <template #header>
          <span class="card-dot" />结果摘要
        </template>
        <JsonViewer :data="task.result_summary" />
      </el-card>

      <!-- Actions -->
      <el-card class="detail-card">
        <template #header>
          <span class="card-dot" />操作
        </template>
        <div class="actions">
          <el-button
            type="primary"
            :disabled="task.status !== 'completed'"
            @click="showConversionDrawer = true"
          >
            🔄 导出为 ONNX
          </el-button>
          <el-button disabled title="等后端 API 就绪后激活">
            📦 注册到模型仓库
          </el-button>
        </div>
      </el-card>

      <ConversionDrawer
        v-model="showConversionDrawer"
        :task-id="task.id"
        :task-name="task.task_name"
        @submitted="loadTask"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import TaskStatusTag from './TaskStatusTag.vue'
import ConversionDrawer from './ConversionDrawer.vue'
import JsonViewer from '@/shared/components/JsonViewer.vue'
import { getTrainingDetail, type TrainingTaskSummary } from '@/shared/api/modules/training'
import { formatTime } from '@/shared/utils/format'

const props = defineProps<{ id: string }>()
const router = useRouter()

const task = ref<TrainingTaskSummary | null>(null)
const loading = ref(true)
const showConversionDrawer = ref(false)

async function loadTask() {
  loading.value = true
  try {
    task.value = await getTrainingDetail(Number(props.id))
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadTask() })
</script>

<style scoped>
.detail-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}
.detail-header h2 {
  font-size: 20px;
  font-weight: 700;
}
.detail-card {
  margin-bottom: 16px;
}
.actions {
  display: flex;
  gap: 10px;
}
</style>
