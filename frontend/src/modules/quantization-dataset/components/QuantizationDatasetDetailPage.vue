<template>
  <div>
    <PageHeader
      :title="dataset?.name || '量化图片管理'"
      subtitle="上传图片后，系统自动维护 ref_img_list.txt"
    >
      <template #actions>
        <el-button @click="router.push('/quantization-datasets')">返回列表</el-button>
        <el-button :disabled="!images.length" @click="toggleSelectPage">
          {{ allPageSelected ? '取消全选' : '全选本页' }}
        </el-button>
        <el-button :disabled="!selectedNames.size" type="danger" plain @click="removeSelected">
          批量删除（{{ selectedNames.size }}）
        </el-button>
        <el-button type="primary" :loading="uploading" @click="chooseFiles">上传图片</el-button>
        <input
          ref="fileInput"
          class="file-input"
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.bmp,.webp,image/jpeg,image/png,image/bmp,image/webp"
          @change="uploadFiles"
        />
      </template>
    </PageHeader>

    <div v-if="dataset" class="summary-card">
      <div><span>图片数量</span><strong>{{ dataset.image_count }}</strong></div>
      <div><span>总大小</span><strong>{{ formatBytes(dataset.size_bytes) }}</strong></div>
      <div class="list-path">
        <span>图片列表</span>
        <code>{{ dataset.image_list_path }}</code>
        <el-button link type="primary" @click="downloadList">下载TXT</el-button>
      </div>
    </div>

    <el-alert
      v-if="uploading"
      :title="`正在上传 ${uploadProgress.current}/${uploadProgress.total}：${uploadProgress.name}`"
      type="info"
      show-icon
      :closable="false"
      class="upload-alert"
    />

    <div v-loading="loading" class="image-grid">
      <div
        v-for="image in images"
        :key="image.name"
        class="image-card"
        :class="{ selected: selectedNames.has(image.name) }"
      >
        <el-checkbox
          :model-value="selectedNames.has(image.name)"
          class="image-check"
          @change="toggleSelected(image.name)"
        />
        <button class="image-button" type="button" @click="openPreview(image)">
          <img :src="imageUrl(image.name)" :alt="image.name" loading="lazy" />
        </button>
        <div class="image-meta">
          <el-tooltip :content="image.name" placement="top">
            <span class="image-name">{{ image.name }}</span>
          </el-tooltip>
          <span>{{ formatBytes(image.size_bytes) }} · {{ formatTime(image.modified_at) }}</span>
        </div>
      </div>
      <el-empty v-if="!loading && !images.length" description="暂无图片，请上传量化样本" />
    </div>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[24, 48, 96]"
        layout="total, sizes, prev, pager, next, jumper"
        @change="fetchImages"
      />
    </div>

    <el-dialog v-model="previewVisible" :title="previewImage?.name" width="88vw" top="5vh">
      <div class="large-preview">
        <img
          v-if="previewImage"
          :src="imageUrl(previewImage.name)"
          :alt="previewImage.name"
        />
      </div>
      <template #footer>
        <span v-if="previewImage">
          {{ formatBytes(previewImage.size_bytes) }} · {{ formatTime(previewImage.modified_at) }}
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/shared/components/PageHeader.vue'
import { formatBytes, formatTime } from '@/shared/utils/format'
import {
  deleteQuantizationImages,
  getQuantizationDataset,
  getQuantizationImages,
  quantizationImageListUrl,
  quantizationImageUrl,
  uploadQuantizationImage,
  type QuantizationDatasetItem,
  type QuantizationImageItem,
} from '@/shared/api/modules/quantization-datasets'

const route = useRoute()
const router = useRouter()
const datasetId = Number(route.params.id)
const dataset = ref<QuantizationDatasetItem>()
const images = ref<QuantizationImageItem[]>([])
const loading = ref(false)
const uploading = ref(false)
const page = ref(1)
const pageSize = ref(24)
const total = ref(0)
const selectedNames = ref(new Set<string>())
const fileInput = ref<HTMLInputElement>()
const uploadProgress = reactive({ current: 0, total: 0, name: '' })
const previewVisible = ref(false)
const previewImage = ref<QuantizationImageItem>()
const allPageSelected = computed(
  () => images.value.length > 0 && images.value.every(image => selectedNames.value.has(image.name)),
)

function imageUrl(name: string) {
  return quantizationImageUrl(datasetId, name)
}

async function fetchDataset() {
  dataset.value = await getQuantizationDataset(datasetId)
}

async function fetchImages() {
  loading.value = true
  try {
    const data = await getQuantizationImages(datasetId, {
      page: page.value,
      page_size: pageSize.value,
    })
    images.value = data.items
    total.value = data.total
    selectedNames.value = new Set()
  } finally {
    loading.value = false
  }
}

function chooseFiles() {
  fileInput.value?.click()
}

async function uploadFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return
  uploading.value = true
  uploadProgress.total = files.length
  let succeeded = 0
  try {
    for (let index = 0; index < files.length; index += 1) {
      uploadProgress.current = index + 1
      uploadProgress.name = files[index].name
      try {
        dataset.value = (await uploadQuantizationImage(datasetId, files[index])).dataset
        succeeded += 1
      } catch {
        // The HTTP client already displays the concrete error; continue the batch.
      }
    }
    page.value = 1
    await Promise.all([fetchDataset(), fetchImages()])
    if (succeeded) ElMessage.success(`成功上传 ${succeeded} 张图片`)
    if (succeeded < files.length) ElMessage.warning(`${files.length - succeeded} 张图片上传失败`)
  } finally {
    uploading.value = false
  }
}

function toggleSelected(name: string) {
  const next = new Set(selectedNames.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  selectedNames.value = next
}

function toggleSelectPage() {
  selectedNames.value = allPageSelected.value
    ? new Set()
    : new Set(images.value.map(image => image.name))
}

async function removeSelected() {
  const names = Array.from(selectedNames.value)
  await ElMessageBox.confirm(
    `确认删除选中的 ${names.length} 张图片吗？ref_img_list.txt 将自动更新。`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  dataset.value = await deleteQuantizationImages(datasetId, names)
  ElMessage.success('删除成功')
  if (images.value.length === names.length && page.value > 1) page.value -= 1
  await fetchImages()
}

function openPreview(image: QuantizationImageItem) {
  previewImage.value = image
  previewVisible.value = true
}

function downloadList() {
  window.open(quantizationImageListUrl(datasetId), '_blank')
}

onMounted(async () => {
  if (!Number.isInteger(datasetId) || datasetId <= 0) {
    await router.replace('/quantization-datasets')
    return
  }
  await Promise.all([fetchDataset(), fetchImages()])
})
</script>

<style scoped>
.file-input { display: none; }
.summary-card {
  display: flex;
  align-items: center;
  gap: 34px;
  margin-bottom: 16px;
  padding: 14px 18px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
}
.summary-card > div { display: flex; align-items: center; gap: 10px; }
.summary-card span { color: var(--txt2); font-size: 12px; }
.summary-card strong { color: var(--txt); font-size: 16px; }
.summary-card .list-path { min-width: 0; flex: 1; }
.list-path code { overflow: hidden; color: var(--cyan); text-overflow: ellipsis; white-space: nowrap; }
.upload-alert { margin-bottom: 16px; }
.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
  min-height: 280px;
}
.image-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel);
}
.image-card.selected { border-color: var(--cyan); box-shadow: 0 0 0 1px var(--cyan); }
.image-check { position: absolute; z-index: 2; top: 8px; left: 9px; padding: 3px 6px; border-radius: 5px; background: rgba(3, 10, 26, 0.75); }
.image-button { display: block; width: 100%; height: 170px; padding: 0; border: 0; background: #071127; cursor: zoom-in; }
.image-button img { display: block; width: 100%; height: 100%; object-fit: contain; }
.image-meta { display: flex; flex-direction: column; gap: 5px; padding: 10px 12px; color: var(--txt2); font-size: 11px; }
.image-name { overflow: hidden; color: var(--txt); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 18px; }
.large-preview { display: grid; place-items: center; height: 76vh; overflow: auto; background: #050b19; }
.large-preview img { max-width: 100%; max-height: 100%; object-fit: contain; }
:deep(.el-empty) { grid-column: 1 / -1; }
</style>
