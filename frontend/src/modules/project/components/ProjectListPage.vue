<template>
  <div class="project-list-page">
    <PageHeader title="项目管理" subtitle="维护项目标识与关联数据集">
      <template #actions>
        <el-button :icon="Refresh" circle @click="handleRefresh" />
        <el-button type="primary" @click="openCreateDrawer">
          新建项目
        </el-button>
      </template>
    </PageHeader>

    <div class="filter-card glow-card">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">Project</span>
          <el-input
            v-model="projectFilter"
            class="filter-input filter-input-project"
            placeholder="按 project 查询"
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
      <el-table-column prop="project" label="Project" min-width="180" show-overflow-tooltip />
      <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="epochs" label="epochs" width="96" />
      <el-table-column prop="batch" label="batch" width="96" />
      <el-table-column prop="imgsz" label="imgsz" width="96" />
      <el-table-column label="绑定数据集" min-width="260">
        <template #default="{ row }">
          <div class="dataset-tag-list">
            <el-tag
              v-for="dataset in resolveDatasets(row.dataset_ids).slice(0, 3)"
              :key="dataset.id"
              size="small"
              effect="plain"
              class="dataset-tag"
            >
              {{ dataset.name }}
            </el-tag>
            <span v-if="resolveDatasets(row.dataset_ids).length > 3" class="dataset-more">
              +{{ resolveDatasets(row.dataset_ids).length - 3 }}
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

    <ProjectFormDrawer
      v-model="showDrawer"
      :project-item="editingProject"
      :datasets="datasets"
      @saved="handleSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { getDatasetList, type DatasetItem } from '@/shared/api/modules/datasets'
import { deleteProject, type ProjectItem } from '@/shared/api/modules/projects'
import { formatTime } from '@/shared/utils/format'
import { useProjectList } from '../composables/useProjectList'
import ProjectFormDrawer from './ProjectFormDrawer.vue'

const {
  items,
  loading,
  page,
  pageSize,
  total,
  projectFilter,
  nameFilter,
  onPageChange,
  onSizeChange,
  fetchList,
  resetFilters,
} = useProjectList()

const showDrawer = ref(false)
const editingProject = ref<ProjectItem | null>(null)
const datasets = ref<DatasetItem[]>([])

const datasetMap = computed(() =>
  Object.fromEntries(datasets.value.map(item => [item.id, item])),
)

function resolveDatasets(ids: number[]) {
  return ids
    .map(id => datasetMap.value[id])
    .filter((item): item is DatasetItem => Boolean(item))
}

async function fetchDatasets() {
  const data = await getDatasetList({ page: 1, page_size: 200 })
  datasets.value = data.items
}

function openCreateDrawer() {
  editingProject.value = null
  showDrawer.value = true
}

function openEditDrawer(projectItem: unknown) {
  editingProject.value = projectItem as ProjectItem
  showDrawer.value = true
}

async function handleDelete(projectItem: unknown) {
  const item = projectItem as ProjectItem
  await ElMessageBox.confirm(
    `确认物理删除项目「${item.name}」吗？此操作不可恢复。`,
    '删除确认',
    {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    },
  )
  await deleteProject(item.id)
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
  await Promise.all([fetchList(), fetchDatasets()])
}

async function handleRefresh() {
  await Promise.all([fetchList(), fetchDatasets()])
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

:deep(.filter-input-project) {
  width: 260px;
}

:deep(.filter-input-name) {
  width: 220px;
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

.dataset-tag-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.dataset-tag {
  border-color: rgba(40, 224, 224, 0.24);
  background: rgba(40, 224, 224, 0.08);
  color: var(--txt);
}

.dataset-more {
  font-size: 12px;
  color: var(--muted);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
