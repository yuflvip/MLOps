<template>
  <header class="app-header">
    <div class="logo" @click="router.push('/')">
      <div class="mark">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
          <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" stroke="#dbeafe" stroke-width="1.5" stroke-linejoin="round" />
          <path d="M12 8l-4 2v4l4 2 4-2v-4l-4-2z" stroke="#28e0e0" stroke-width="1.5" stroke-linejoin="round" />
        </svg>
      </div>
      <h1>M<b>LOps</b></h1>
    </div>
    <div class="spacer" />
    <span class="clock font-mono">{{ clock }}</span>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const clock = ref('')
let timer: ReturnType<typeof setInterval> | null = null

function tick() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  clock.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

onMounted(() => {
  tick()
  timer = setInterval(tick, 1000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 22px;
  height: 60px;
  background: linear-gradient(180deg, rgba(18, 40, 80, 0.85), rgba(10, 22, 48, 0.6));
  border-bottom: 1px solid var(--line2);
  backdrop-filter: blur(6px);
}
.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}
.mark {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: linear-gradient(145deg, #08162f, #102b57, #071226);
  border: 1px solid rgba(109, 197, 255, 0.32);
  box-shadow: var(--glow);
}
.logo h1 {
  font-size: 19px;
  letter-spacing: 1.4px;
  font-weight: 700;
  color: var(--txt);
}
.logo h1 b {
  color: var(--cyan);
}
.spacer {
  flex: 1;
}
.clock {
  font-size: 13px;
  color: var(--txt2);
  border-left: 1px solid var(--line);
  padding-left: 18px;
}
</style>
