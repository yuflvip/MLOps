<template>
  <nav class="app-sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div
      v-for="item in navItems"
      :key="item.path"
      class="nav-item"
      :class="{ active: isActive(item.path) }"
      @click="router.push(item.path)"
    >
      <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
      <span v-if="!appStore.sidebarCollapsed" class="nav-label">{{ item.label }}</span>
    </div>

    <div class="nav-divider" />

    <div
      v-for="item in placeholderItems"
      :key="item.path"
      class="nav-item"
      :class="{ active: isActive(item.path) }"
      @click="router.push(item.path)"
    >
      <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
      <span v-if="!appStore.sidebarCollapsed" class="nav-label">{{ item.label }}</span>
      <span v-if="!appStore.sidebarCollapsed" class="nav-tag">规划中</span>
    </div>

    <div class="nav-bottom">
      <div class="nav-item" @click="appStore.toggleSidebar()">
        <el-icon class="nav-icon">
          <Fold v-if="!appStore.sidebarCollapsed" />
          <Expand v-else />
        </el-icon>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { Aim, Document, Box, User, Fold, Expand } from '@element-plus/icons-vue'
import { useAppStore } from '@/shared/stores/app'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const navItems = [
  { path: '/training', label: '训练任务', icon: Aim },
  { path: '/template', label: '模板管理', icon: Document },
]

const placeholderItems = [
  { path: '/model-registry', label: '模型仓库', icon: Box },
  { path: '/auth', label: '用户管理', icon: User },
]

function isActive(path: string): boolean {
  return route.path.startsWith(path)
}
</script>

<style scoped>
.app-sidebar {
  padding: 14px 12px;
  border-right: 1px solid var(--line);
  overflow-y: auto;
  background: linear-gradient(180deg, rgba(14, 29, 61, 0.5), transparent);
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  width: 220px;
  flex-shrink: 0;
}
.app-sidebar.collapsed {
  width: 56px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 13px;
  border-radius: 10px;
  cursor: pointer;
  color: var(--txt2);
  font-size: 13.5px;
  margin-bottom: 3px;
  border: 1px solid transparent;
  transition: 0.18s;
  position: relative;
}
.nav-item:hover {
  background: var(--panel);
  color: var(--txt);
}
.nav-item.active {
  background: linear-gradient(90deg, rgba(40, 224, 224, 0.16), rgba(59, 130, 246, 0.06));
  color: #fff;
  border-color: var(--line2);
}
.nav-item.active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 3px;
  background: var(--cyan);
  box-shadow: var(--glow);
}
.nav-icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}
.nav-label {
  white-space: nowrap;
}
.nav-tag {
  margin-left: auto;
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.2);
  color: var(--teal);
}
.nav-divider {
  height: 1px;
  background: var(--line);
  margin: 12px 0;
}
.nav-bottom {
  margin-top: auto;
}
</style>
