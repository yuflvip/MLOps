<template>
  <div class="task-list-page">
    <PageHeader title="训练任务">
      <template #actions>
        <el-select
          v-model="statusFilter"
          placeholder="状态筛选"
          clearable
          style="width: 140px"
        >
          <el-option label="排队中" value="queued" />
          <el-option label="运行中" value="in_progress" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
          <el-option label="已停止" value="stopped" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-button :icon="Refresh" circle @click="fetchList" />
        <el-button type="primary" @click="showCreateDrawer = true">
          创建训练任务
        </el-button>
      </template>
    </PageHeader>

    <el-table
      :data="items"
      v-loading="loading"
      stripe
      :default-sort="{ prop: 'created_at', order: 'descending' }"
      @row-click="handleRowClick"
      style="cursor: pointer"
    >
      <el-table-column prop="task_name" label="任务名称" min-width="180" show-overflow-tooltip sortable />
      <el-table-column prop="template_name" label="模板" width="140" show-overflow-tooltip sortable />
      <el-table-column prop="status" label="状态" width="110" sortable>
        <template #default="{ row }">
          <TaskStatusTag :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column prop="queue_name" label="队列" width="140" show-overflow-tooltip sortable />
      <el-table-column prop="created_at" label="创建时间" width="170" sortable>
        <template #default="{ row }">
          <span class="font-mono">{{ formatTime(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="goDetail(row.id)">
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>

    <CreateTaskDrawer v-model="showCreateDrawer" @created="fetchList" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import TaskStatusTag from './TaskStatusTag.vue'
import CreateTaskDrawer from './CreateTaskDrawer.vue'
import { useTrainingList } from '../composables/useTrainingList'
import { formatTime } from '@/shared/utils/format'

const router = useRouter()
const { items, loading, page, pageSize, total, statusFilter, onPageChange, onSizeChange, fetchList } = useTrainingList()

const showCreateDrawer = ref(false)

function handleRowClick(row: { id: number }) {
  router.push(`/training/${row.id}`)
}

function goDetail(id: number) {
  router.push(`/training/${id}`)
}

onMounted(() => { fetchList() })
</script>

<style scoped>
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
