<template>
  <el-drawer v-model="visible" title="权重打包" size="min(780px, 100vw)" :close-on-click-modal="false" :close-on-press-escape="!building" :show-close="!building">
    <el-form label-position="top">
      <div class="source-platform-row">
      <el-form-item label="源模型"><el-input :model-value="sourceFile" readonly /></el-form-item>
      <el-form-item label="端侧平台">
        <el-select v-model="platform" :disabled="building || previewing" @change="invalidatePlatform">
          <el-option v-for="value in packagePlatforms" :key="value" :label="value" :value="value" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="platform === '3403'" label="3403运行时">
        <el-select v-model="runtime" :disabled="building || previewing" @change="preview = undefined">
          <el-option label="按转换记录自动识别" value="" /><el-option label="SVP" value="3403svp" /><el-option label="NNN / Ascend" value="3403nnn" />
        </el-select>
      </el-form-item>
      </div>
      <el-form-item label="包名称（可修改）">
        <el-input v-model="packageName" :disabled="building || previewing" placeholder="留空按默认规则生成，支持自定义 .tgz 名称" @input="preview = undefined" />
        <el-button link type="primary" :disabled="building" @click="resetName">恢复默认名称</el-button>
      </el-form-item>
    </el-form>
    <el-button :loading="previewing" :disabled="building" @click="loadPreview">{{ preview ? '刷新预览' : '预览打包内容' }}</el-button>
    <template v-if="preview">
      <el-descriptions :column="1" border class="package-info">
        <el-descriptions-item label="包名称">{{ preview.package_name }}</el-descriptions-item>
        <el-descriptions-item label="存放路径">{{ preview.local_path }}</el-descriptions-item>
        <el-descriptions-item label="运行时">{{ preview.runtime }}</el-descriptions-item>
      </el-descriptions>
      <el-alert v-if="preview.exists" title="已存在该包名，点击打包后可选择覆盖或取消" type="warning" :closable="false" />
      <el-tabs v-model="previewTab">
        <el-tab-pane label="文件清单" name="files"><pre>{{ preview.files.join('\n') }}</pre></el-tab-pane>
        <el-tab-pane label="cfg" name="cfg"><pre>{{ preview.cfg_content }}</pre></el-tab-pane>
        <el-tab-pane label="names" name="names"><pre>{{ preview.names_content }}</pre></el-tab-pane>
        <el-tab-pane label="mklink.sh（755）" name="script"><pre>{{ preview.script }}</pre></el-tab-pane>
      </el-tabs>
    </template>
    <template #footer>
      <el-button :disabled="building" @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="building" :disabled="!preview" @click="build">打包</el-button>
      <el-button :disabled="building" @click="router.push('/weight-packages')">查看权重包</el-button>
    </template>
  </el-drawer>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { packagePlatforms, previewPackage, createPackage, type PackagePreview, type PackageInput, type PackagePlatform } from '@/shared/api/modules/weightPackages'
const visible = defineModel<boolean>({ required: true })
const props = defineProps<{ expId: number; sourceFile: string; initialPackageName?: string; initialPlatform?: PackagePlatform; initialRuntime?: string }>()
const emit = defineEmits<{ (event: 'saved'): void }>()
const router = useRouter()
const platform = ref<PackagePlatform>('x86')
const runtime = ref<'' | '3403svp' | '3403nnn'>('')
const packageName = ref('')
const preview = ref<PackagePreview>()
const previewTab = ref('cfg')
let previewRequestId = 0
const previewing = ref(false)
const building = ref(false)
watch(visible, (value) => {
  if (!value) {
    previewRequestId += 1
    previewing.value = false
    return
  }
  const extension = props.sourceFile.split('.').pop()?.toLowerCase()
  platform.value = extension === 'om' ? '3403' : extension === 'bin' ? '692' : extension === 'rknn' ? '3588' : 'x86'
  platform.value = props.initialPlatform || platform.value
  runtime.value = props.initialRuntime === '3403svp' || props.initialRuntime === '3403nnn' ? props.initialRuntime : ''
  packageName.value = props.initialPackageName || ''
  preview.value = undefined
  previewTab.value = 'cfg'
  void loadPreview()
}, { immediate: true })
function input(): PackageInput { return { exp_id: props.expId, source_file: props.sourceFile, platform: platform.value, package_name: packageName.value.trim() || undefined, runtime: platform.value === '3403' ? runtime.value || undefined : undefined } }
function invalidatePlatform() { preview.value = undefined; packageName.value = '' }
function resetName() { packageName.value = ''; preview.value = undefined; loadPreview() }
async function loadPreview() {
  const requestId = ++previewRequestId
  preview.value = undefined; previewing.value = true
  try {
    const data = await previewPackage(input())
    if (requestId !== previewRequestId || !visible.value) return
    preview.value = data
    packageName.value = data.package_name
  } catch {
    // Request errors are shown by the shared API interceptor.
  } finally {
    if (requestId === previewRequestId) previewing.value = false
  }
}
async function build() {
  const current = preview.value
  if (!current) return
  let overwrite = false
  if (current.exists) {
    try { await ElMessageBox.confirm(`已存在 ${current.package_name}，是否覆盖本地压缩包及解包目录？覆盖后需重新上传FTP。`, '同名包确认', { confirmButtonText: '覆盖', cancelButtonText: '取消', type: 'warning' }); overwrite = true } catch { return }
  }
  building.value = true
  try {
    await createPackage({ ...input(), overwrite, preview_token: current.preview_token })
    ElMessage.success('权重包已生成，可在权重包管理中下载或上传FTP'); visible.value = false; emit('saved')
  } catch { preview.value = undefined } finally { building.value = false }
}
</script>
<style scoped>
.source-platform-row { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1.4fr); gap: 12px; }
.source-platform-row .el-select { width: 100%; }
.package-info { margin: 18px 0; overflow-wrap: anywhere; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; line-height: 1.7; }
</style>
