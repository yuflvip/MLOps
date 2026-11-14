<template>
  <PageHeader title="权重包管理" subtitle="查看本地权重包、下载及上传FTP">
    <template #actions><el-button :loading="loading" @click="fetchList">刷新</el-button></template>
  </PageHeader>
  <el-form inline @submit.prevent="search">
    <el-form-item label="模型类型">
      <el-select v-model="modelType" clearable placeholder="全部类型" style="width: 140px">
        <el-option label="分类器" value="classification" /><el-option label="检测器" value="detection" /><el-option label="轮廓分割" value="segmentation" />
      </el-select>
    </el-form-item>
    <el-form-item label="模型族">
      <el-select v-model="projectId" filterable clearable placeholder="全部模型族" style="width: 200px">
        <el-option v-for="project in filteredProjects" :key="project.id" :label="project.name + ' (' + project.project + ')'" :value="project.id" />
      </el-select>
    </el-form-item>
    <el-form-item label="模型 / 包名 / 实验"><el-input v-model="keyword" clearable placeholder="输入关键词" @keyup.enter="search" /></el-form-item>
    <el-form-item label="端侧平台"><el-select v-model="platform" clearable placeholder="全部平台" style="width: 140px"><el-option v-for="p in packagePlatforms" :key="p" :value="p" :label="p" /></el-select></el-form-item>
    <el-form-item label="FTP 状态"><el-select v-model="uploadStatus" clearable placeholder="全部" style="width: 140px"><el-option label="未上传" value="pending" /><el-option label="上传中" value="uploading" /><el-option label="已上传" value="succeeded" /><el-option label="上传失败" value="failed" /></el-select></el-form-item>
    <el-form-item><el-button type="primary" @click="search">查询</el-button><el-button @click="reset">重置</el-button></el-form-item>
  </el-form>
  <el-table :data="items" v-loading="loading" stripe>
    <el-table-column label="序号" width="75"><template #default="{ $index }">{{ (page - 1) * pageSize + $index + 1 }}</template></el-table-column>
    <el-table-column label="包名称 / 模型族" min-width="280" show-overflow-tooltip>
      <template #default="{ row }">
        <div class="package-name">{{ row.package_name }}</div>
        <div class="package-family">{{ row.project_key }}</div>
      </template>
    </el-table-column>
    <el-table-column label="模型族名称" min-width="160" show-overflow-tooltip>
      <template #default="{ row }">{{ projectNames.get(row.project_id) || '-' }}</template>
    </el-table-column>
    <el-table-column label="实验名称" min-width="190" show-overflow-tooltip>
      <template #default="{ row }">
        <RouterLink class="experiment-link" :to="{ name: 'ExpDetail', params: { id: row.exp_id }, query: { from: 'weight-packages' } }">{{ row.exp_name }}</RouterLink>
      </template>
    </el-table-column>
    <el-table-column prop="platform" label="端侧平台" width="100" />
    <el-table-column label="包大小" width="110"><template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template></el-table-column>
    <el-table-column label="打包时间" width="175"><template #default="{ row }">{{ formatTime(row.created_at) }}</template></el-table-column>
    <el-table-column label="FTP 状态" width="165"><template #default="{ row }"><el-tag :type="row.upload_status === 'failed' ? 'danger' : row.ftp_uploaded ? 'success' : 'info'">{{ uploadLabel(row as WeightPackage) }}</el-tag></template></el-table-column>
    <el-table-column label="操作" width="180" fixed="right"><template #default="{ row }">
      <div class="package-actions">
        <el-button link type="primary" @click="showDetails(row as WeightPackage)">详情</el-button>
        <el-button link type="primary" @click="downloadPackage(row as WeightPackage)">下载</el-button>
        <el-dropdown trigger="click" :disabled="busyId !== undefined">
          <el-button link type="primary" :loading="busyId === row.id" :disabled="busyId !== undefined">更多</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="repackage(row as WeightPackage)">重新打包</el-dropdown-item>
              <el-dropdown-item @click="upload(row as WeightPackage)">上传FTP</el-dropdown-item>
              <el-dropdown-item divided @click="removePackage(row as WeightPackage)"><span class="delete-action">删除</span></el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </template></el-table-column>
  </el-table>
  <WeightPackageDetailDrawer v-model="detailVisible" :item="detailItem" />
  <WeightPackageDrawer v-if="repackItem" v-model="repackVisible" :exp-id="repackItem.exp_id" :source-file="repackItem.source_file" :initial-platform="repackItem.platform as PackagePlatform" :initial-runtime="repackItem.runtime" :initial-package-name="repackItem.package_name" @saved="fetchList" />
  <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="fetchList" @size-change="search" class="pagination" />
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import PageHeader from '@/shared/components/PageHeader.vue'
import WeightPackageDetailDrawer from './WeightPackageDetailDrawer.vue'
import WeightPackageDrawer from './WeightPackageDrawer.vue'
import { getProjectList, type ProjectItem } from '@/shared/api/modules/projects'
import { formatTime, formatBytes } from '@/shared/utils/format'
import { packagePlatforms, listPackages, uploadPackage, downloadPackage, checkPackageDeletion, deletePackage, type WeightPackage, type PackagePlatform } from '@/shared/api/modules/weightPackages'
const items = ref<WeightPackage[]>([])
const detailVisible = ref(false)
const detailItem = ref<WeightPackage>()
function showDetails(item: WeightPackage) { detailItem.value = item; detailVisible.value = true }
const keyword = ref(''); const platform = ref(''); const uploadStatus = ref('')
const modelType = ref(''); const projectId = ref<number>()
const projects = ref<ProjectItem[]>([])
const projectNames = computed(() => new Map(projects.value.map(project => [project.id, project.name])))
const repackVisible = ref(false); const repackItem = ref<WeightPackage>()
const filteredProjects = computed(() => projects.value.filter(project => !modelType.value || project.model_type === modelType.value))
watch(filteredProjects, options => {
  if (projectId.value != null && !options.some(project => project.id === projectId.value)) projectId.value = undefined
}, { flush: 'sync' })
async function loadProjects() {
  const all: ProjectItem[] = []
  let nextPage = 1
  while (true) {
    const data = await getProjectList({ page: nextPage, page_size: 200 })
    all.push(...data.items)
    if (all.length >= data.total || data.items.length === 0) break
    nextPage += 1
  }
  projects.value = all
}
function repackage(item: WeightPackage) { repackItem.value = item; repackVisible.value = true }
const page = ref(1); const pageSize = ref(20); const total = ref(0)
const loading = ref(false); const busyId = ref<number>()
let requestId = 0
async function fetchList() {
  const current = ++requestId; loading.value = true
  try {
    const data = await listPackages({ page: page.value, page_size: pageSize.value, keyword: keyword.value.trim() || undefined, platform: platform.value || undefined, model_type: modelType.value || undefined, project_id: projectId.value, upload_status: uploadStatus.value || undefined })
    if (current === requestId) {
      items.value = data.items; total.value = data.total
      const updated = data.items.find(item => item.id === detailItem.value?.id)
      if (updated) detailItem.value = updated
    }
  } finally { if (current === requestId) loading.value = false }
}
function search() { page.value = 1; fetchList() }
function reset() { keyword.value = ''; platform.value = ''; uploadStatus.value = ''; modelType.value = ''; projectId.value = undefined; search() }
function uploadLabel(item: WeightPackage) {
  if (item.upload_status === 'uploading') return '上传中'
  if (item.upload_status === 'failed') return item.ftp_uploaded ? '已上传（重传失败）' : '上传失败'
  return item.ftp_uploaded ? '已上传' : '未上传'
}
async function upload(item: WeightPackage) {
  const overwrite = item.ftp_uploaded
  try {
    await ElMessageBox.confirm(
      overwrite ? `该包已上传FTP，是否覆盖远端文件？\n${item.package_name}` : `确认上传该权重包到FTP？\n${item.package_name}`,
      overwrite ? '覆盖确认' : '上传确认',
      { confirmButtonText: overwrite ? '覆盖' : '上传', cancelButtonText: '取消', type: overwrite ? 'warning' : 'info' },
    )
  } catch { return }
  busyId.value = item.id
  try {
    try { await uploadPackage(item.id, overwrite) } catch (error) {
      if (!axios.isAxiosError(error) || error.response?.status !== 409 || !String(error.response.data?.message).includes('FTP已存在同名')) throw error
      try { await ElMessageBox.confirm('FTP已存在同名文件，是否覆盖？', '上传确认', { confirmButtonText: '覆盖', cancelButtonText: '取消', type: 'warning' }) } catch { return }
      await uploadPackage(item.id, true)
    }
    ElMessage.success('FTP上传完成')
  } catch { /* API interceptor displays real failures, not overwrite confirmation. */ } finally { busyId.value = undefined; await fetchList() }
}
async function removePackage(item: WeightPackage) {
  busyId.value = item.id
  try {
    const check = await checkPackageDeletion(item.id)
    if (!check.allowed || !check.confirmation_token) {
      ElMessage.warning(check.message)
      return
    }
    try {
      await ElMessageBox.confirm(`确认删除 ${item.package_name}？将删除记录、本地tgz文件及解包文件夹。`, '删除确认', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    } catch { return }
    await deletePackage(item.id, check.confirmation_token)
    ElMessage.success('权重包已删除')
    if (detailItem.value?.id === item.id) { detailVisible.value = false; detailItem.value = undefined }
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await fetchList()
  } catch { /* API interceptor displays validation or deletion failures. */ } finally { busyId.value = undefined }
}
onMounted(() => { loadProjects(); fetchList() })
</script>
<style scoped>
.pagination { margin-top: 20px; justify-content: flex-end; }
.package-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.package-family { font-size: 12px; color: var(--el-text-color-secondary); }
.experiment-link { color: var(--el-color-primary); text-decoration: none; }
.experiment-link:hover { text-decoration: underline; }
.package-actions { display: flex; align-items: center; gap: 12px; }
.package-actions .el-button + .el-button { margin-left: 0; }
.delete-action { color: var(--el-color-danger); }
</style>
