<template>
  <div class="dataset-list-page">
    <PageHeader title="数据集管理" subtitle="管理训练页面可复用的数据集基础信息">
      <template #actions>
        <el-button :icon="Refresh" circle @click="fetchList" />
        <el-button type="primary" @click="openCreateDrawer">
          新建数据集
        </el-button>
      </template>
    </PageHeader>

    <div class="filter-card glow-card">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">名称</span>
          <el-input
            v-model="nameFilter"
            class="filter-input filter-input-name"
            placeholder="按名称查询"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">路径</span>
          <el-input
            v-model="pathFilter"
            class="filter-input filter-input-path"
            placeholder="按路径查询"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">任务类型</span>
          <el-select
            v-model="taskTypeFilter"
            class="filter-input filter-input-type"
            placeholder="全部"
            clearable
          >
            <el-option label="分类" value="classification" />
            <el-option label="检测" value="detection" />
            <el-option label="分割" value="segmentation" />
          </el-select>
        </el-form-item>
        <div class="filter-actions">
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </div>
      </el-form>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column label="序号" width="60">
        <template #default="{ $index }">
          {{ (page - 1) * pageSize + $index + 1 }}
        </template>
      </el-table-column>
      <el-table-column prop="name" label="数据集名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="path" label="本地路径" min-width="260" show-overflow-tooltip />
      <el-table-column prop="task_type" label="任务类型" width="100">
        <template #default="{ row }">
          <span>{{ taskTypeLabel(row.task_type) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分类类别" min-width="280">
        <template #default="{ row }">
          <div class="class-tag-list">
            <el-tag
              v-for="name in row.class_names.slice(0, 5)"
              :key="name"
              size="small"
              effect="plain"
              class="class-tag"
            >
              {{ name }}
            </el-tag>
            <span v-if="row.class_names.length > 5" class="class-more">
              +{{ row.class_names.length - 5 }}
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述 / 备注" min-width="180" show-overflow-tooltip />
      <el-table-column prop="updated_at" label="修改时间" width="170">
        <template #default="{ row }">
          <span class="font-mono">{{ formatTime(row.updated_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEditDrawer(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
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
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <DatasetFormDrawer
      v-model="showDrawer"
      :dataset="editingDataset"
      @saved="fetchList"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { deleteDataset, type DatasetItem } from '@/shared/api/modules/datasets'
import { formatTime } from '@/shared/utils/format'
import { useDatasetList } from '../composables/useDatasetList'
import DatasetFormDrawer from './DatasetFormDrawer.vue'

const {
  items,
  loading,
  page,
  pageSize,
  total,
  nameFilter,
  pathFilter,
  taskTypeFilter,
  onPageChange,
  onSizeChange,
  fetchList,
  resetFilters,
} = useDatasetList()

const showDrawer = ref(false)
const editingDataset = ref<DatasetItem | null>(null)

function taskTypeLabel(value: string | null) {
  if (value === 'classification') return '分类'
  if (value === 'detection') return '检测'
  if (value === 'segmentation') return '分割'
  return '-'
}

function openCreateDrawer() {
  editingDataset.value = null
  showDrawer.value = true
}

function openEditDrawer(dataset: unknown) {
  editingDataset.value = dataset as DatasetItem
  showDrawer.value = true
}

async function handleDelete(dataset: unknown) {
  const item = dataset as DatasetItem
  await ElMessageBox.confirm(
    `确认物理删除数据集「${item.name}」吗？此操作不可恢复。`,
    '删除确认',
    {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    },
  )
  await deleteDataset(item.id)
  await fetchList()
}

async function handleSearch() {
  onPageChange(1)
  await fetchList()
}

async function handleReset() {
  resetFilters()
  await fetchList()
}

async function handlePageChange(currentPage: number) {
  onPageChange(currentPage)
  await fetchList()
}

async function handleSizeChange(size: number) {
  onSizeChange(size)
  await fetchList()
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.filter-card {
  margin-bottom: 16px;
  padding: 16px 18px 6px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(15, 31, 67, 0.86), rgba(10, 21, 47, 0.92));
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.16);
}

.filter-form {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px 14px;
  overflow-x: auto;
  padding-bottom: 2px;
}

:deep(.inline-filter-item .el-form-item__content) {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
}

:deep(.inline-filter-item) {
  margin-bottom: 0;
  flex: 0 0 auto;
}

:deep(.filter-input-name) {
  width: 220px;
}

:deep(.filter-input-path) {
  width: 320px;
}

:deep(.filter-input-type) {
  width: 170px;
}

.inline-filter-label {
  font-size: 12.5px;
  color: var(--txt2);
  white-space: nowrap;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 0;
  flex: 0 0 auto;
}

.class-tag-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.class-tag {
  border-color: rgba(40, 224, 224, 0.24);
  background: rgba(40, 224, 224, 0.08);
  color: var(--txt);
}

.class-more {
  font-size: 12px;
  color: var(--muted);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
