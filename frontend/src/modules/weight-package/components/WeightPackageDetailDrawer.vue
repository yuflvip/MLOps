<template>
  <el-drawer v-model="visible" title="权重包详情" size="min(760px, 96vw)" destroy-on-close>
    <div v-if="item" class="package-detail">
      <el-descriptions title="基本信息" :column="1" border>
        <el-descriptions-item label="包名称">{{ item.package_name }}</el-descriptions-item>
        <el-descriptions-item label="模型族标识">{{ item.project_key }}</el-descriptions-item>
        <el-descriptions-item label="实验名称">
          <RouterLink class="experiment-link" :to="{ name: 'ExpDetail', params: { id: item.exp_id }, query: { from: 'weight-packages' } }">{{ item.exp_name }}</RouterLink>
        </el-descriptions-item>
        <el-descriptions-item label="端侧平台">{{ item.platform }}</el-descriptions-item>
        <el-descriptions-item label="包大小">{{ formatBytes(item.size_bytes) }}</el-descriptions-item>
        <el-descriptions-item label="模型打包时间">{{ formatTime(item.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <el-descriptions title="模型信息" :column="1" border>
        <el-descriptions-item label="模型类型">{{ modelTypeLabel(item.model_type) }}</el-descriptions-item>
        <el-descriptions-item label="模型框架">{{ item.model_framework || '-' }}</el-descriptions-item>
        <el-descriptions-item label="模型尺寸">{{ item.model_size || '-' }}</el-descriptions-item>
        <el-descriptions-item label="运行时">{{ item.runtime || '-' }}</el-descriptions-item>
        <el-descriptions-item label="训练结束时间">{{ formatTime(item.training_finished_at) }}</el-descriptions-item>
        <el-descriptions-item label="源模型文件"><code>{{ item.source_file }}</code></el-descriptions-item>
        <el-descriptions-item label="模型文件 MD5"><code>{{ item.model_md5 || '未记录（重新打包后生成）' }}</code></el-descriptions-item>
      </el-descriptions>
      <el-descriptions title="文件信息" :column="1" border>
        <el-descriptions-item label="本地路径"><code>{{ item.local_path }}</code></el-descriptions-item>
        <el-descriptions-item label="解包目录"><code>{{ item.unpacked_path }}</code></el-descriptions-item>
        <el-descriptions-item label="压缩包 SHA256"><code>{{ item.sha256 || '-' }}</code></el-descriptions-item>
      </el-descriptions>
      <el-descriptions title="FTP 上传信息" :column="1" border>
        <el-descriptions-item label="FTP 状态">
          <el-tag :type="item.upload_status === 'failed' ? 'danger' : item.ftp_uploaded ? 'success' : 'info'">{{ uploadLabel }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="FTP 文件路径"><code>{{ item.ftp_path || '-' }}</code></el-descriptions-item>
        <el-descriptions-item label="上传时间">{{ formatTime(item.ftp_uploaded_at) }}</el-descriptions-item>
        <el-descriptions-item label="上传错误"><span class="upload-error">{{ item.upload_error || '-' }}</span></el-descriptions-item>
      </el-descriptions>
    </div>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button v-if="item" type="primary" @click="downloadPackage(item)">下载权重包</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { downloadPackage, type WeightPackage } from '@/shared/api/modules/weightPackages'
import { formatBytes, formatTime } from '@/shared/utils/format'

const props = defineProps<{ item?: WeightPackage }>()
const visible = defineModel<boolean>({ required: true })
const uploadLabel = computed(() => {
  const item = props.item
  if (!item) return '-'
  if (item.upload_status === 'uploading') return '上传中'
  if (item.upload_status === 'failed') return item.ftp_uploaded ? '已上传（重传失败）' : '上传失败'
  return item.ftp_uploaded ? '已上传' : '未上传'
})
function modelTypeLabel(value: string | null) {
  const labels: Record<string, string> = { classification: '分类器', detection: '检测器', segmentation: '轮廓分割' }
  return value ? labels[value] || value : '-'
}
</script>

<style scoped>
.package-detail { display: grid; gap: 24px; }
.package-detail :deep(.el-descriptions__table) { table-layout: fixed; }
.package-detail :deep(.el-descriptions__label) { width: 130px; }
.package-detail :deep(.el-descriptions__content) { overflow-wrap: anywhere; }
.experiment-link { color: var(--el-color-primary); text-decoration: none; }
.experiment-link:hover { text-decoration: underline; }
.upload-error { white-space: pre-wrap; }
</style>
