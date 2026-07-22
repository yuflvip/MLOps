<template>
  <div class="model-registry-page">
    <PageHeader title="模型仓库" subtitle="导入、审核并管理正式模型版本">
      <template #actions>
        <el-button :icon="Refresh" circle title="刷新" @click="handleRefresh" />
        <el-button type="primary" :icon="Upload" @click="openImportDialog">导入实验</el-button>
      </template>
    </PageHeader>

    <div class="filter-card glow-card">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">模型族</span>
          <el-select
            v-model="projectIdFilter"
            class="project-filter"
            placeholder="全部模型族"
            filterable
            clearable
          >
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">状态</span>
          <el-select v-model="statusFilter" class="status-filter" placeholder="全部状态" clearable>
            <el-option label="待审核" value="pending_review" />
            <el-option label="已审核" value="approved" />
            <el-option label="审核不通过" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item class="inline-filter-item">
          <span class="inline-filter-label">模型类型</span>
          <el-select v-model="modelTypeFilter" class="status-filter" placeholder="全部类型" clearable>
            <el-option label="分类器" value="classification" />
            <el-option label="检测器" value="detection" />
            <el-option label="轮廓分割" value="segmentation" />
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
        <template #default="{ $index }">{{ (page - 1) * pageSize + $index + 1 }}</template>
      </el-table-column>
      <el-table-column label="模型族" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ projectName(row.project_id) }}</template>
      </el-table-column>
      <el-table-column prop="name" label="实验名称" min-width="190" show-overflow-tooltip>
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row as ExpItem)">{{ row.name }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="resolved_path" label="实验路径" min-width="300" show-overflow-tooltip>
        <template #default="{ row }"><span class="font-mono path-text">{{ row.resolved_path }}</span></template>
      </el-table-column>
      <el-table-column prop="version" label="正式版本" width="120">
        <template #default="{ row }"><span class="font-mono">{{ row.version || '-' }}</span></template>
      </el-table-column>
      <el-table-column label="mAP/Acc" width="170">
        <template #default="{ row }">
          <span class="font-mono">{{ formatValidationMetric(row.validation_metric_value) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="开始训练" width="170">
        <template #default="{ row }">
          <span class="font-mono">{{ formatTime(row.training_started_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="结束训练" width="170">
        <template #default="{ row }">
          <span class="font-mono">{{ formatTime(row.training_finished_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.review_status)" effect="dark" size="small">
            {{ statusLabel(row.review_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="imported_at" label="导入时间" width="170">
        <template #default="{ row }"><span class="font-mono">{{ formatTime(row.imported_at) }}</span></template>
      </el-table-column>
      <el-table-column prop="reviewed_at" label="审核时间" width="170">
        <template #default="{ row }"><span class="font-mono">{{ formatTime(row.reviewed_at) }}</span></template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-dropdown trigger="click" @command="handleRowCommand($event, row as ExpItem)">
            <el-button link type="primary" size="small">
              更多
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="detail">详情</el-dropdown-item>
                <el-dropdown-item
                  v-if="row.review_status !== 'approved'"
                  command="approve"
                >
                  审核通过
                </el-dropdown-item>
                <el-dropdown-item
                  v-if="row.review_status === 'pending_review'"
                  command="reject"
                  divided
                >
                  审核不通过
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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

    <el-dialog v-model="importVisible" title="导入实验" width="680px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="模型族" required>
          <el-select
            v-model="importProjectId"
            placeholder="选择模型族后扫描实验目录"
            filterable
            style="width: 100%"
            @change="scanCandidates"
          >
            <el-option
              v-for="project in importableProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <div v-if="candidateRoot" class="root-path">
        <span>实验根路径</span>
        <code>{{ candidateRoot }}</code>
      </div>

      <el-table
        v-if="importProjectId"
        :data="candidates"
        v-loading="candidateLoading"
        max-height="360"
        @selection-change="selectedCandidates = $event"
      >
        <el-table-column type="selection" width="48" :selectable="row => !row.already_imported" />
        <el-table-column prop="name" label="实验目录" min-width="260" show-overflow-tooltip />
        <el-table-column prop="modified_at" label="目录修改时间" width="170">
          <template #default="{ row }">{{ formatTime(row.modified_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.already_imported ? 'info' : 'success'" size="small" effect="plain">
              {{ row.already_imported ? '已导入' : '可导入' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="importing"
          :disabled="selectedCandidates.length === 0"
          @click="handleImport"
        >
          导入选中实验
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="approveVisible" title="审核实验" width="520px" :close-on-click-modal="false">
      <el-form ref="approveFormRef" :model="approveForm" :rules="approveRules" label-position="top">
        <el-form-item label="实验">
          <el-input :model-value="approvingExp?.name" disabled />
        </el-form-item>
        <el-form-item label="正式版本号" prop="version">
          <el-input v-model="approveForm.version" placeholder="例如 v1.0" />
        </el-form-item>
        <el-form-item label="版本说明">
          <el-input v-model="approveForm.description" type="textarea" :rows="3" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveVisible = false">取消</el-button>
        <el-button type="primary" :loading="approving" @click="handleApprove">确认审核</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { ArrowDown, Refresh, Upload } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { getProjectList, type ProjectItem } from '@/shared/api/modules/projects'
import {
  approveExp,
  getExpCandidates,
  importExps,
  rejectExp,
  type ExpCandidate,
  type ExpItem,
  type ExpReviewStatus,
} from '@/shared/api/modules/exps'
import { formatTime } from '@/shared/utils/format'
import { useExpList } from '../composables/useExpList'

const {
  items, loading, page, pageSize, total, projectIdFilter, statusFilter, modelTypeFilter,
  onPageChange, onSizeChange, fetchList, resetFilters,
} = useExpList()
const router = useRouter()

const projects = ref<ProjectItem[]>([])
const importVisible = ref(false)
const importProjectId = ref<number>()
const candidateRoot = ref('')
const candidates = ref<ExpCandidate[]>([])
const selectedCandidates = ref<ExpCandidate[]>([])
const candidateLoading = ref(false)
const importing = ref(false)
const approveVisible = ref(false)
const approvingExp = ref<ExpItem>()
const approving = ref(false)
const approveFormRef = ref<FormInstance>()
const approveForm = reactive({ version: '', description: '' })
const approveRules: FormRules<typeof approveForm> = {
  version: [{ required: true, message: '请输入正式版本号', trigger: 'blur' }],
}

const projectMap = computed(() => Object.fromEntries(projects.value.map(project => [project.id, project])))
const importableProjects = computed(() => projects.value.filter(project => Boolean(project.exp_root_path)))

function projectName(projectId: number) {
  return projectMap.value[projectId]?.name || `模型族 #${projectId}`
}

function statusLabel(status: ExpReviewStatus) {
  if (status === 'approved') return '已审核'
  if (status === 'rejected') return '审核不通过'
  return '待审核'
}

function statusTagType(status: ExpReviewStatus) {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

function formatValidationMetric(value: number | null) {
  return value == null ? '-' : String(value)
}

function openDetail(exp: ExpItem) {
  router.push(`/model-registry/exps/${exp.id}`)
}

function handleRowCommand(command: string, exp: ExpItem) {
  if (command === 'detail') {
    openDetail(exp)
    return
  }
  if (command === 'approve') {
    openApproveDialog(exp)
    return
  }
  if (command === 'reject') {
    handleReject(exp)
  }
}

async function fetchProjects() {
  const data = await getProjectList({ page: 1, page_size: 200 })
  projects.value = data.items
}

function openImportDialog() {
  importProjectId.value = undefined
  candidateRoot.value = ''
  candidates.value = []
  selectedCandidates.value = []
  importVisible.value = true
}

async function scanCandidates() {
  if (!importProjectId.value) return
  selectedCandidates.value = []
  candidateLoading.value = true
  try {
    const data = await getExpCandidates(importProjectId.value)
    candidateRoot.value = data.exp_root_path
    candidates.value = data.items
  } finally {
    candidateLoading.value = false
  }
}

async function handleImport() {
  if (!importProjectId.value || selectedCandidates.value.length === 0) return
  importing.value = true
  try {
    await importExps(importProjectId.value, selectedCandidates.value.map(item => item.relative_path))
    ElMessage.success(`已导入 ${selectedCandidates.value.length} 条实验`)
    importVisible.value = false
    await fetchList()
  } finally {
    importing.value = false
  }
}

function openApproveDialog(exp: ExpItem) {
  approvingExp.value = exp
  approveForm.version = ''
  approveForm.description = ''
  approveVisible.value = true
}

async function handleApprove() {
  if (!approvingExp.value || !approveFormRef.value) return
  await approveFormRef.value.validate()
  approving.value = true
  try {
    await approveExp(approvingExp.value.id, {
      version: approveForm.version.trim(),
      description: approveForm.description.trim() || null,
    })
    ElMessage.success('实验已审核为正式版本')
    approveVisible.value = false
    await fetchList()
  } finally {
    approving.value = false
  }
}

async function handleReject(exp: ExpItem) {
  const { value } = await ElMessageBox.prompt(
    `请输入实验「${exp.name}」审核不通过的原因。`,
    '审核不通过',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputValidator: value => Boolean(value.trim()) || '请输入审核意见',
    },
  )
  await rejectExp(exp.id, value.trim())
  ElMessage.success('已标记为审核不通过')
  await fetchList()
}

async function handleSearch() { onPageChange(1); await fetchList() }
async function handleReset() { resetFilters(); await fetchList() }
async function handlePageChange(value: number) { onPageChange(value); await fetchList() }
async function handleSizeChange(value: number) { onSizeChange(value); await fetchList() }
async function handleRefresh() { await Promise.all([fetchProjects(), fetchList()]) }

onMounted(handleRefresh)
</script>

<style scoped>
.filter-card { margin-bottom: 16px; padding: 16px 18px 6px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }
.filter-form { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px; }
:deep(.inline-filter-item) { margin-bottom: 10px; }
:deep(.inline-filter-item .el-form-item__content) { display: flex; gap: 10px; flex-wrap: nowrap; }
.inline-filter-label { font-size: 12.5px; color: var(--txt2); white-space: nowrap; }
.project-filter { width: 240px; }
.status-filter { width: 150px; }
.filter-actions { display: flex; gap: 8px; margin-bottom: 10px; }
.path-text { font-size: 12px; color: var(--txt2); }
.dropdown-icon { margin-left: 4px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
.root-path { display: grid; gap: 6px; padding: 10px 12px; margin-bottom: 12px; border-left: 3px solid var(--cyan); background: rgba(40, 224, 224, 0.06); }
.root-path span { color: var(--txt2); font-size: 12px; }
.root-path code { overflow-wrap: anywhere; color: var(--txt); }
@media (max-width: 720px) {
  .project-filter { width: min(240px, 58vw); }
  .status-filter { width: min(150px, 42vw); }
}
</style>
