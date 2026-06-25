<template>
  <div class="runtime-environment-list-page">
    <PageHeader title="运行环境管理" subtitle="维护训练与导出任务的执行环境">
      <template #actions>
        <el-button :icon="Refresh" circle @click="handleRefresh" />
        <el-button type="primary" @click="openCreateDrawer">
          新建运行环境
        </el-button>
      </template>
    </PageHeader>

    <div class="filter-card glow-card">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">标识</span>
          <el-input
            v-model="codeFilter"
            class="filter-input filter-input-code"
            placeholder="按标识查询"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
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
          <span class="inline-filter-label">环境类型</span>
          <el-select
            v-model="envTypeFilter"
            class="filter-input filter-input-type"
            placeholder="全部"
            clearable
          >
            <el-option label="Python" value="python" />
            <el-option label="Conda" value="conda" />
            <el-option label="Docker" value="docker" />
          </el-select>
        </el-form-item>
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">状态</span>
          <el-select
            v-model="isActiveFilter"
            class="filter-input filter-input-status"
            placeholder="全部"
          >
            <el-option label="全部" value="all" />
            <el-option label="启用" value="true" />
            <el-option label="停用" value="false" />
          </el-select>
        </el-form-item>
        <div class="filter-actions">
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </div>
      </el-form>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column label="序号" width="72">
        <template #default="{ $index }">
          {{ (page - 1) * pageSize + $index + 1 }}
        </template>
      </el-table-column>
      <el-table-column prop="code" label="标识" min-width="180" show-overflow-tooltip />
      <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="env_type" label="环境类型" width="110">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ formatEnvType(row.env_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="python_path" label="Python 路径" min-width="260" show-overflow-tooltip />
      <el-table-column prop="docker_image" label="Docker 镜像" min-width="220" show-overflow-tooltip />
      <el-table-column prop="working_dir" label="工作目录" min-width="220" show-overflow-tooltip />
      <el-table-column label="额外环境变量" width="120">
        <template #default="{ row }">
          {{ Object.keys(row.extra_env).length }}
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="96">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="light">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="修改时间" width="170">
        <template #default="{ row }">
          <span class="font-mono">{{ formatTime(row.updated_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
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

    <RuntimeEnvironmentFormDrawer
      v-model="showDrawer"
      :runtime-environment-item="editingItem"
      @saved="handleSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import {
  deleteRuntimeEnvironment,
  type RuntimeEnvironmentItem,
} from '@/shared/api/modules/runtime-environments'
import { formatTime } from '@/shared/utils/format'
import { useRuntimeEnvironmentList } from '../composables/useRuntimeEnvironmentList'
import RuntimeEnvironmentFormDrawer from './RuntimeEnvironmentFormDrawer.vue'

const {
  items,
  loading,
  page,
  pageSize,
  total,
  codeFilter,
  nameFilter,
  envTypeFilter,
  isActiveFilter,
  onPageChange,
  onSizeChange,
  fetchList,
  resetFilters,
} = useRuntimeEnvironmentList()

const showDrawer = ref(false)
const editingItem = ref<RuntimeEnvironmentItem | null>(null)

function formatEnvType(value: RuntimeEnvironmentItem['env_type']) {
  if (value === 'python') return 'Python'
  if (value === 'docker') return 'Docker'
  return 'Conda'
}

function openCreateDrawer() {
  editingItem.value = null
  showDrawer.value = true
}

function openEditDrawer(item: unknown) {
  editingItem.value = item as RuntimeEnvironmentItem
  showDrawer.value = true
}

async function handleDelete(item: unknown) {
  const runtimeEnvironment = item as RuntimeEnvironmentItem
  await ElMessageBox.confirm(
    `确认物理删除运行环境「${runtimeEnvironment.name}」吗？此操作不可恢复。`,
    '删除确认',
    {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    },
  )
  await deleteRuntimeEnvironment(runtimeEnvironment.id)
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

async function handleSaved() {
  await fetchList()
}

async function handleRefresh() {
  await fetchList()
}

onMounted(() => {
  handleRefresh()
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

:deep(.filter-input-code) {
  width: 220px;
}

:deep(.filter-input-name) {
  width: 220px;
}

:deep(.filter-input-type) {
  width: 150px;
}

:deep(.filter-input-status) {
  width: 120px;
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
  flex: 0 0 auto;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
