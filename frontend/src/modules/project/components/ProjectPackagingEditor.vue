<template>
  <template v-if="section === 'links'">
  <div class="link-grid">
    <el-form-item label="模型软链接主名称" prop="packaging.model_links" :rules="modelLinkRules">
      <el-input v-model="modelLinkBase" placeholder="vehicle_base_classifier" />
    </el-form-item>
    <el-form-item label="cfg 软链接名称" prop="packaging.cfg_link" :rules="fileRules('.cfg', true)">
      <el-input v-model="config.cfg_link" placeholder="自动生成，可修改" />
    </el-form-item>
    <el-form-item label="names 软链接名称" prop="packaging.names_link" :rules="fileRules('.names', true)">
      <el-input v-model="config.names_link" placeholder="自动生成，可修改" />
    </el-form-item>
  </div>
  <p class="hint platform-hint">
    <span>692、530 自动使用 .bin，其他平台自动使用 .weights。留空表示暂未配置。</span>
    <el-tooltip placement="bottom" trigger="hover" :show-after="150">
      <template #content>
        <div v-for="platform in packagingPlatforms" :key="platform" class="platform-detail">
          {{ platform }}：{{ config.model_links[platform] || '未配置' }}
        </div>
      </template>
      <el-icon class="platform-info" tabindex="0" aria-label="查看各平台完整模型软链接名称">
        <InfoFilled />
      </el-icon>
    </el-tooltip>
  </p>
  </template>
  <template v-else>
  <el-tabs v-model="activeFile">
    <el-tab-pane label="cfg 文件" name="cfg">
      <el-form-item label="包内 cfg 文件名" >
        <el-input :model-value="cfgFilename" readonly />
      </el-form-item>
      <div class="file-actions">
        <el-button @click="cfgInput?.click()">导入 cfg</el-button>
        <el-button @click="download('cfg')">下载 cfg</el-button>
        <input ref="cfgInput" type="file" accept=".cfg" hidden @change="importFile($event, 'cfg')" />
      </div>
      <el-input v-model="config.cfg_content" type="textarea" :rows="12" placeholder="上传或直接编辑 cfg 原文" />
    </el-tab-pane>
    <el-tab-pane label="names 文件" name="names">
      <el-form-item label="包内 names 文件名" >
        <el-input :model-value="namesFilename" readonly />
      </el-form-item>
      <div class="file-actions">
        <el-button @click="namesInput?.click()">导入 names</el-button>
        <el-button @click="download('names')">下载 names</el-button>
        <input ref="namesInput" type="file" accept=".names" hidden @change="importFile($event, 'names')" />
        <span>{{ classCount }} 个类别</span>
      </div>
      <el-input v-model="config.names_content" type="textarea" :rows="12" placeholder="每行一个类别，保持模型训练时的类别顺序" />
      <p class="hint">类别从 0 开始，按行顺序对应模型输出。更换类别定义后，打包时需确认与所选模型版本一致。</p>
    </el-tab-pane>
  </el-tabs>
  </template>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import type { FormItemRule } from 'element-plus'
import { packagingPlatforms, type ProjectPackagingConfig } from '@/shared/api/modules/projects'
const config = defineModel<ProjectPackagingConfig>({ required: true })
const props = defineProps<{ projectKey: string; section: 'links' | 'files' }>()
const cfgFilename = computed(() => props.projectKey.trim() ? props.projectKey.trim() + '.cfg' : '')
const namesFilename = computed(() => props.projectKey.trim() ? props.projectKey.trim() + '.names' : '')
watch([cfgFilename, namesFilename], ([cfg, names]) => {
  config.value.cfg_filename = cfg
  config.value.names_filename = names
}, { immediate: true })
const activeFile = ref('cfg')
const cfgInput = ref<HTMLInputElement>()
const namesInput = ref<HTMLInputElement>()
const classCount = computed(() => config.value.names_content.split(/\r?\n/).filter(line => line.trim()).length)
function fileRules(suffix: string, optional = false): FormItemRule[] {
  return [{ validator: (_rule, value: string, callback) => {
    const name = (value || '').trim()
    if (!name && optional) return callback()
    if (!name || name.length > 255 || /[\\/:*?"<>|\s\x00-\x1f]/.test(name) || !name.endsWith(suffix)) {
      return callback(new Error(`请输入有效文件名，不能包含路径或空白，须以 ${suffix} 结尾`))
    }
    callback()
  }, trigger: 'blur' }]
}
const modelLinkBase = computed({
  get: () => Object.values(config.value.model_links).find(Boolean)?.replace(/\.(bin|weights)$/, '') || '',
  set: (value: string) => {
    const base = value.trim()
    config.value.cfg_link = base ? base + '.cfg' : ''
    config.value.names_link = base ? base + '.names' : ''
    config.value.model_links = base ? Object.fromEntries(packagingPlatforms.map(platform =>
      [platform, base + (platform === '692' || platform === '530' ? '.bin' : '.weights')])) : {}
  },
})
const modelLinkRules: FormItemRule[] = [{ validator: (_rule, _value, callback) => {
  const name = modelLinkBase.value
  if (name && (name.length > 247 || /[\\/:*?"<>|\s\x00-\x1f]/.test(name) || /\.(bin|weights)$/.test(name))) {
    return callback(new Error('请输入不含后缀的有效主名称，不能包含路径或空白'))
  }
  callback()
}, trigger: 'blur' }]
async function importFile(event: Event, kind: 'cfg' | 'names') {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    if (file.size > 1024 * 1024) throw new Error('文件不能超过 1 MB')
    if (!file.name.endsWith('.' + kind)) throw new Error(`请选择 .${kind} 文件`)
    const text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer())
    config.value[`${kind}_content`] = text.replace(/\r\n?/g, '\n')
    ElMessage.success('已导入，请保存模型族以提交修改')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取失败，请使用 UTF-8 编码文件')
  } finally { input.value = '' }
}
function download(kind: 'cfg' | 'names') {
  const url = URL.createObjectURL(new Blob([config.value[`${kind}_content`]], { type: 'text/plain;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = (kind === 'cfg' ? cfgFilename.value : namesFilename.value) || ('model.' + kind)
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
</script>

<style scoped>
.hint { color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.6; margin: 0 0 16px; }
.link-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.platform-hint { display: flex; align-items: center; gap: 6px; }
.platform-info { cursor: help; color: var(--el-color-info); flex-shrink: 0; }
.platform-detail { line-height: 1.8; overflow-wrap: anywhere; max-width: min(480px, 80vw); }
.file-actions { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
@media (max-width: 600px) { .link-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.link-grid { grid-template-columns: 1fr; } }
</style>
