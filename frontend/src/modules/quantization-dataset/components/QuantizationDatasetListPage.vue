<template>
  <div>
    <PageHeader title="量化数据集" subtitle="管理模型转换使用的量化样本图片">
      <template #actions>
        <el-button :icon="Refresh" circle @click="fetchList" />
        <el-button type="primary" @click="openCreate">新建量化数据集</el-button>
      </template>
    </PageHeader>

    <div class="filter-card">
      <el-input
        v-model="keyword"
        clearable
        placeholder="按名称查询"
        @keyup.enter="handleSearch"
      />
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column label="序号" width="70">
        <template #default="{ $index }">{{ (page - 1) * pageSize + $index + 1 }}</template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="image_count" label="图片数量" width="100" />
      <el-table-column label="总大小" width="110">
        <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column prop="image_list_path" label="ref_img_list.txt" min-width="320" show-overflow-tooltip />
      <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column label="修改时间" width="170">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="245" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openImages(row)">图片管理</el-button>
          <el-button link type="primary" @click="downloadList(row)">下载TXT</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="removeDataset(row)">删除</el-button>
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
        @change="fetchList"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑量化数据集' : '新建量化数据集'" width="520px">
      <el-form label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="128" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { formatBytes, formatTime } from '@/shared/utils/format'
import {
  createQuantizationDataset,
  deleteQuantizationDataset,
  getQuantizationDatasetList,
  quantizationImageListUrl,
  updateQuantizationDataset,
  type QuantizationDatasetItem,
} from '@/shared/api/modules/quantization-datasets'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const items = ref<QuantizationDatasetItem[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')
const dialogVisible = ref(false)
const editing = ref<QuantizationDatasetItem | null>(null)
const form = reactive({ name: '', description: '' })

async function fetchList() {
  loading.value = true
  try {
    const data = await getQuantizationDatasetList({
      page: page.value,
      page_size: pageSize.value,
      name: keyword.value.trim() || undefined,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.description = ''
  dialogVisible.value = true
}

function openEdit(row: unknown) {
  const item = row as QuantizationDatasetItem
  editing.value = item
  form.name = item.name
  form.description = item.description || ''
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  saving.value = true
  try {
    const payload = { name: form.name, description: form.description || null }
    if (editing.value) await updateQuantizationDataset(editing.value.id, payload)
    else await createQuantizationDataset(payload)
    dialogVisible.value = false
    ElMessage.success('保存成功')
    await fetchList()
  } finally {
    saving.value = false
  }
}

function openImages(row: unknown) {
  const item = row as QuantizationDatasetItem
  router.push(`/quantization-datasets/${item.id}`)
}

function downloadList(row: unknown) {
  const item = row as QuantizationDatasetItem
  window.open(quantizationImageListUrl(item.id), '_blank')
}

async function removeDataset(row: unknown) {
  const item = row as QuantizationDatasetItem
  await ElMessageBox.confirm(
    `确认删除量化数据集「${item.name}」及其中 ${item.image_count} 张图片吗？此操作不可恢复。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  await deleteQuantizationDataset(item.id)
  ElMessage.success('删除成功')
  if (items.value.length === 1 && page.value > 1) page.value -= 1
  await fetchList()
}

async function handleSearch() {
  page.value = 1
  await fetchList()
}

async function handleReset() {
  keyword.value = ''
  page.value = 1
  await fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.filter-card {
  display: flex;
  gap: 10px;
  width: 520px;
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
}
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 18px; }
</style>
