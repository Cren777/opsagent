<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: 'online' | 'offline' | 'unknown' }>()

const type = computed(() => {
  return props.status === 'online' ? 'success' : props.status === 'offline' ? 'danger' : 'info'
})

const label = computed(() => {
  return props.status === 'online' ? '已连接' : props.status === 'offline' ? '未连接' : '未知'
})
</script>

<template>
  <span class="status-badge">
    <span class="status-dot" :class="status" />
    <el-tag :type="type" size="small">{{ label }}</el-tag>
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online {
  background: #67c23a;
  box-shadow: 0 0 4px #67c23a;
}

.status-dot.offline {
  background: #f56c6c;
}

.status-dot.unknown {
  background: #909399;
}
</style>
