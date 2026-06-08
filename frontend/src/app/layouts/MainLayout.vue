<template>
  <div class="main-layout">
    <AppHeader />
    <div class="main-body">
      <AppSidebar />
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
</script>

<style scoped>
.main-layout {
  display: grid;
  grid-template-rows: 60px 1fr;
  height: 100vh;
}
.main-body {
  display: flex;
  overflow: hidden;
}
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 40px;
}
</style>
