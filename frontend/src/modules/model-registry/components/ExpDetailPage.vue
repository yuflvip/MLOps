<template>
  <div class="exp-detail-page">
    <PageHeader :title="exp?.name || '实验详情'" subtitle="训练产物实时读取自实验目录">
      <template #actions>
        <el-button :icon="ArrowLeft" @click="router.push('/model-registry')">返回</el-button>
        <el-button :icon="Refresh" circle title="刷新产物" @click="loadPage" />
      </template>
    </PageHeader>

    <div v-if="exp" class="summary-band">
      <div><span>模型族</span><strong>{{ project?.name || `模型族 #${exp.project_id}` }}</strong></div>
      <div><span>正式版本</span><strong class="font-mono">{{ exp.version || '-' }}</strong></div>
      <div>
        <span>状态</span>
        <strong :class="['status-text', exp.review_status]">
          {{ statusLabel(exp.review_status) }}
        </strong>
      </div>
      <div>
        <span>mAP/Acc</span>
        <strong class="font-mono">{{ formatValidationMetric(exp.validation_metric_value) }}</strong>
      </div>
      <div><span>训练开始</span><strong class="font-mono">{{ formatTime(exp.training_started_at) }}</strong></div>
      <div><span>训练结束</span><strong class="font-mono">{{ formatTime(exp.training_finished_at) }}</strong></div>
      <div class="path-summary"><span>实验路径</span><code>{{ exp.resolved_path }}</code></div>
      <div v-if="exp.review_comment" class="review-comment"><span>审核意见</span><strong>{{ exp.review_comment }}</strong></div>
    </div>

    <el-tabs v-model="activeTab" class="detail-tabs">
      <el-tab-pane label="训练产物" name="artifacts">
        <div class="section-heading">
          <p>共 {{ artifacts.length }} 个文件，点击文件名称查看原始内容</p>
        </div>

        <el-table :data="artifacts" v-loading="loading" stripe>
          <el-table-column label="序号" type="index" width="72" />
          <el-table-column label="文件名称" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <el-button link type="primary" @click="openPreview(row as ExpArtifactItem)">
                {{ row.name }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column prop="relative_path" label="相对路径" min-width="300" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="font-mono path-text">{{ row.relative_path }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="size_bytes" label="大小" width="120">
            <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
          </el-table-column>
          <el-table-column prop="modified_at" label="修改时间" width="170">
            <template #default="{ row }">
              <span class="font-mono">{{ formatTime(row.modified_at) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="模型产物" name="models">
        <div class="section-heading">
          <p>共 {{ modelArtifacts.length }} 个模型文件</p>
        </div>

        <el-table :data="modelArtifacts" v-loading="loading" stripe>
          <el-table-column label="序号" type="index" width="72" />
          <el-table-column prop="name" label="模型名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="md5" label="Hash (MD5)" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="font-mono hash-text">{{ row.md5 }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="relative_path" label="相对路径" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="font-mono path-text">{{ row.relative_path }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="size_bytes" label="大小" width="120">
            <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
          </el-table-column>
          <el-table-column prop="modified_at" label="修改时间" width="170">
            <template #default="{ row }">
              <span class="font-mono">{{ formatTime(row.modified_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="290" fixed="right">
            <template #default="{ row }">
              <div class="model-actions">
                <el-button link type="primary" size="small" @click="downloadModel(row as ExpModelArtifactItem)">
                  下载
                </el-button>
                <el-button
                  v-if="isPtArtifact(row as ExpModelArtifactItem)"
                  type="primary"
                  size="small"
                  :disabled="project?.model_architecture !== 'HGNetV2'"
                  @click="openOnnxExport(row as ExpModelArtifactItem)"
                >
                  导出ONNX
                </el-button>
                <el-dropdown
                  v-if="isOnnxArtifact(row as ExpModelArtifactItem)"
                  split-button
                  type="primary"
                  size="small"
                  @click="handlePlatformConversion('hisi3403', row as ExpModelArtifactItem)"
                  @command="handlePlatformConversion($event, row as ExpModelArtifactItem)"
                >
                  导出海思3403
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="novatek692">联咏692</el-dropdown-item>
                      <el-dropdown-item command="rk3588">RK3588</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyState description="暂无模型产物" />
          </template>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="转换记录" name="exports">
        <el-table :data="conversionRecords" stripe>
          <el-table-column label="序号" type="index" width="72" />
          <el-table-column prop="source_file" label="源文件" min-width="190" show-overflow-tooltip />
          <el-table-column label="转换类型" width="150">
            <template #default="{ row }">{{ conversionTypeLabel(row.converter_code) }}</template>
          </el-table-column>
          <el-table-column prop="output_file" label="输出文件" min-width="220" show-overflow-tooltip />
          <el-table-column label="参数" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ conversionParamsLabel(row as ModelConversionItem) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="conversionStatusType(row.status)" size="small">
                {{ conversionStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="完成时间" width="170">
            <template #default="{ row }">{{ formatTime(row.finished_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.error_message"
                link
                type="danger"
                size="small"
                @click="showConversionError(row as ModelConversionItem)"
              >
                失败原因
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyState description="暂无转换记录" />
          </template>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="previewVisible"
      :title="previewArtifact?.relative_path || '产物预览'"
      width="min(1120px, 92vw)"
      top="5vh"
      destroy-on-close
      @closed="clearBlobUrl"
    >
      <div v-loading="previewLoading" class="preview-body">
        <el-image
          v-if="previewArtifact?.preview_kind === 'image' && blobUrl"
          :src="blobUrl"
          :preview-src-list="[blobUrl]"
          fit="contain"
          class="image-preview"
        />
        <iframe
          v-else-if="previewArtifact?.preview_kind === 'pdf' && blobUrl"
          :src="blobUrl"
          class="pdf-preview"
          title="PDF preview"
        />
        <pre v-else-if="previewData?.content != null" class="text-preview"><code>{{ previewData.content }}</code></pre>
        <template v-else-if="previewData && ['table', 'xlsx'].includes(previewData.preview_kind)">
          <div v-if="previewData.preview_kind === 'xlsx' && previewData.sheet_names.length" class="sheet-bar">
            <span>工作表</span>
            <el-select v-model="selectedSheet" size="small" @change="loadStructuredPreview(1)">
              <el-option v-for="name in previewData.sheet_names" :key="name" :label="name" :value="name" />
            </el-select>
          </div>
          <el-table :data="previewData.rows" border max-height="58vh">
            <el-table-column
              v-for="(column, index) in previewData.columns"
              :key="`${column}-${index}`"
              :label="column || `列 ${index + 1}`"
              min-width="150"
              show-overflow-tooltip
            >
              <template #default="{ row }">{{ row[index] }}</template>
            </el-table-column>
          </el-table>
          <div class="preview-pagination">
            <el-button :disabled="previewPage <= 1" @click="loadStructuredPreview(previewPage - 1)">上一页</el-button>
            <span>第 {{ previewPage }} 页</span>
            <el-button :disabled="!previewData.has_more" @click="loadStructuredPreview(previewPage + 1)">下一页</el-button>
          </div>
        </template>
        <div v-else-if="!previewLoading" class="no-preview">
          该文件为二进制或暂不支持在线预览，可查看文件大小、类型和修改时间。
        </div>
        <el-alert
          v-if="previewData?.truncated"
          title="文件内容较大，当前仅显示前 1 MB。"
          type="warning"
          :closable="false"
          show-icon
          class="preview-alert"
        />
      </div>
    </el-dialog>

    <OnnxExportDrawer
      v-if="exp"
      v-model="exportVisible"
      :exp-id="exp.id"
      :artifact="exportArtifact"
      @submitted="handleConversionSubmitted"
    />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import EmptyState from '@/shared/components/EmptyState.vue'
import OnnxExportDrawer from './OnnxExportDrawer.vue'
import { getProjectDetail, type ProjectItem } from '@/shared/api/modules/projects'
import {
  getExpArtifactBlob,
  getExpArtifactPreview,
  getExpArtifacts,
  getExpDetail,
  getExpModelArtifacts,
  getModelConversions,
  type ExpArtifactItem,
  type ExpArtifactPreviewData,
  type ExpItem,
  type ExpModelArtifactItem,
  type ExpReviewStatus,
  type ModelConversionItem,
  type ModelConversionStatus,
} from '@/shared/api/modules/exps'
import { formatBytes, formatTime } from '@/shared/utils/format'

const props = defineProps<{ id: string }>()
const router = useRouter()
const exp = ref<ExpItem>()
const project = ref<ProjectItem>()
const artifacts = ref<ExpArtifactItem[]>([])
const modelArtifacts = ref<ExpModelArtifactItem[]>([])
const activeTab = ref('artifacts')
const conversionRecords = ref<ModelConversionItem[]>([])
const loading = ref(false)
const exportVisible = ref(false)
const exportArtifact = ref<ExpArtifactItem>()
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewArtifact = ref<ExpArtifactItem>()
const previewData = ref<ExpArtifactPreviewData>()
const previewPage = ref(1)
const selectedSheet = ref<string>()
const blobUrl = ref('')
let pollTimer: ReturnType<typeof setInterval> | undefined

function statusLabel(status: ExpReviewStatus) {
  if (status === 'approved') return '已审核'
  if (status === 'rejected') return '审核不通过'
  return '待审核'
}

function formatValidationMetric(value: number | null) {
  return value == null ? '-' : String(value)
}

function isPtArtifact(artifact: ExpArtifactItem) {
  return ['pt', 'pth'].includes(artifact.extension.toLowerCase())
}

function isOnnxArtifact(artifact: ExpArtifactItem) {
  return artifact.extension.toLowerCase() === 'onnx'
}

function openOnnxExport(artifact: ExpModelArtifactItem) {
  exportArtifact.value = artifact
  exportVisible.value = true
}

async function downloadModel(artifact: ExpModelArtifactItem) {
  try {
    await ElMessageBox.confirm(
      `确认下载模型「${artifact.name}」吗？`,
      '下载确认',
      {
        confirmButtonText: '下载',
        cancelButtonText: '取消',
        type: 'info',
      },
    )
  } catch {
    return
  }
  const blob = await getExpArtifactBlob(Number(props.id), artifact.relative_path)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = artifact.name
  anchor.click()
  URL.revokeObjectURL(url)
}

function handlePlatformConversion(command: string, artifact: ExpModelArtifactItem) {
  const labels: Record<string, string> = {
    hisi3403: '海思3403',
    novatek692: '联咏692',
    rk3588: 'RK3588',
  }
  ElMessage.info(`${artifact.name} 的${labels[command] || command}转换功能待接入`)
}

async function loadPage() {
  const expId = Number(props.id)
  loading.value = true
  try {
    const [detail, artifactData, modelArtifactData, conversionData] = await Promise.all([
      getExpDetail(expId),
      getExpArtifacts(expId),
      getExpModelArtifacts(expId),
      getModelConversions(expId),
    ])
    exp.value = detail
    artifacts.value = artifactData.items
    modelArtifacts.value = modelArtifactData.items
    conversionRecords.value = conversionData.items
    project.value = await getProjectDetail(detail.project_id)
    updatePolling()
  } finally {
    loading.value = false
  }
}

async function loadConversions() {
  const hadActive = conversionRecords.value.some(item =>
    ['queued', 'running'].includes(item.status),
  )
  const data = await getModelConversions(Number(props.id))
  conversionRecords.value = data.items
  const hasActive = data.items.some(item => ['queued', 'running'].includes(item.status))
  if (hadActive && !hasActive) {
    const [artifactData, modelArtifactData] = await Promise.all([
      getExpArtifacts(Number(props.id)),
      getExpModelArtifacts(Number(props.id)),
    ])
    artifacts.value = artifactData.items
    modelArtifacts.value = modelArtifactData.items
  }
  updatePolling()
}

function updatePolling() {
  const hasActive = conversionRecords.value.some(item =>
    ['queued', 'running'].includes(item.status),
  )
  if (hasActive && !pollTimer) {
    pollTimer = setInterval(loadConversions, 2000)
  } else if (!hasActive && pollTimer) {
    clearInterval(pollTimer)
    pollTimer = undefined
  }
}

async function handleConversionSubmitted() {
  activeTab.value = 'exports'
  await loadConversions()
}

function conversionTypeLabel(converterCode: string) {
  if (converterCode === 'hgnet_to_onnx') return 'HGNet → ONNX'
  return converterCode
}

function conversionParamsLabel(item: ModelConversionItem) {
  const params = item.params
  return `${params.device?.toUpperCase() || '-'} / ${params.imgsz || '-'} / opset ${params.opset || '-'}`
}

function conversionStatusLabel(status: ModelConversionStatus) {
  if (status === 'queued') return '排队中'
  if (status === 'running') return '导出中'
  if (status === 'succeeded') return '成功'
  return '失败'
}

function conversionStatusType(status: ModelConversionStatus) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

function showConversionError(item: ModelConversionItem) {
  ElMessageBox.alert(item.error_message || '未知错误', '转换失败', {
    confirmButtonText: '关闭',
  })
}

async function openPreview(artifact: ExpArtifactItem) {
  clearBlobUrl()
  previewArtifact.value = artifact
  previewData.value = undefined
  previewPage.value = 1
  selectedSheet.value = undefined
  previewVisible.value = true
  previewLoading.value = true
  try {
    if (artifact.preview_kind === 'image' || artifact.preview_kind === 'pdf') {
      const blob = await getExpArtifactBlob(Number(props.id), artifact.relative_path)
      blobUrl.value = URL.createObjectURL(blob)
    } else if (!['binary', 'unsupported'].includes(artifact.preview_kind)) {
      await loadStructuredPreview(1)
    }
  } finally {
    previewLoading.value = false
  }
}

async function loadStructuredPreview(page: number) {
  if (!previewArtifact.value) return
  previewLoading.value = true
  try {
    const data = await getExpArtifactPreview(Number(props.id), {
      path: previewArtifact.value.relative_path,
      page,
      page_size: 100,
      sheet_name: selectedSheet.value,
    })
    previewData.value = data
    previewPage.value = page
    selectedSheet.value = data.sheet_name || undefined
  } finally {
    previewLoading.value = false
  }
}

function clearBlobUrl() {
  if (blobUrl.value) URL.revokeObjectURL(blobUrl.value)
  blobUrl.value = ''
}

onMounted(loadPage)
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.summary-band { display: grid; grid-template-columns: 1.2fr .7fr .7fr 2fr; gap: 18px; padding: 16px 18px; margin-bottom: 22px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }
.summary-band > div { display: grid; gap: 6px; min-width: 0; }
.summary-band span, .section-heading p { color: var(--txt2); font-size: 12px; }
.summary-band strong { font-size: 14px; }
.status-text.approved { color: #67c23a; }
.status-text.pending_review { color: #e6a23c; }
.status-text.rejected { color: #f56c6c; }
.summary-band code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--txt); }
.review-comment { grid-column: 1 / -1; }
.detail-tabs { margin-top: 2px; }
:deep(.detail-tabs > .el-tabs__header) { margin-bottom: 16px; }
:deep(.detail-tabs .el-tabs__item) { height: 42px; font-size: 14px; }
.section-heading { display: flex; justify-content: space-between; align-items: end; margin-bottom: 12px; }
.section-heading p { margin: 0; }
.path-text { color: var(--txt2); font-size: 12px; }
.hash-text { font-size: 12px; color: var(--txt2); }
.model-actions { display: flex; align-items: center; gap: 8px; }
.preview-body { min-height: 240px; }
.image-preview { width: 100%; height: min(68vh, 760px); background: #071127; }
:deep(.image-preview img) { max-width: 100%; max-height: 100%; }
.pdf-preview { width: 100%; height: 70vh; border: 1px solid var(--line); }
.text-preview { max-height: 68vh; margin: 0; padding: 14px; overflow: auto; border: 1px solid var(--line); border-radius: 6px; background: #071127; color: var(--txt); font-size: 12.5px; line-height: 1.6; white-space: pre; }
.sheet-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.sheet-bar span { color: var(--txt2); font-size: 12px; }
.sheet-bar .el-select { width: 220px; }
.preview-pagination { display: flex; justify-content: center; align-items: center; gap: 14px; margin-top: 12px; }
.preview-pagination span { color: var(--txt2); font-size: 12px; }
.no-preview { display: grid; place-items: center; min-height: 240px; color: var(--txt2); }
.preview-alert { margin-top: 12px; }
@media (max-width: 900px) {
  .summary-band { grid-template-columns: 1fr 1fr; }
  .path-summary { grid-column: 1 / -1; }
}
</style>
