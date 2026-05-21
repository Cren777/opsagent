<script setup lang="ts">
import type { DataSourceItem } from '@/types/datasource'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const props = defineProps<{ source: DataSourceItem }>()
const emit = defineEmits<{
  edit: [id: string]
  delete: [id: string]
  test: [id: string]
  activate: [id: string]
}>()

const typeIcon: Record<string, string> = {
  mysql: 'DataBoard',
  clickhouse: 'DataAnalysis',
  excel_csv: 'Document',
}

const typeName: Record<string, string> = {
  mysql: 'MySQL',
  clickhouse: 'ClickHouse',
  excel_csv: 'Excel/CSV',
}

function getSummary(source: DataSourceItem): string {
  const c = source.config as unknown as Record<string, unknown>
  if (source.type === 'excel_csv') return (c.file_path as string) || ''
  return `${c.host || ''}:${c.port || ''}/${c.database || ''}`
}
</script>

<template>
  <el-card class="source-card" :class="{ active: source.is_active }" shadow="hover">
    <div class="card-header">
      <div class="card-type">
        <el-icon :size="28" color="#409eff"><component :is="typeIcon[source.type]" /></el-icon>
        <div>
          <div class="card-name">{{ source.name }}</div>
          <div class="card-type-name">{{ typeName[source.type] }}</div>
        </div>
      </div>
      <StatusBadge status="unknown" />
    </div>

    <div class="card-summary">{{ getSummary(source) }}</div>

    <div class="card-actions">
      <el-button size="small" text :icon="'Connection'" @click="emit('test', source.id)">测试</el-button>
      <el-button size="small" text :icon="'Edit'" @click="emit('edit', source.id)">编辑</el-button>
      <el-popconfirm title="确定删除此数据源？" @confirm="emit('delete', source.id)">
        <template #reference>
          <el-button size="small" text type="danger" :icon="'Delete'">删除</el-button>
        </template>
      </el-popconfirm>
      <el-button
        v-if="!source.is_active"
        size="small"
        type="primary"
        plain
        @click="emit('activate', source.id)"
      >
        设为活跃
      </el-button>
      <el-tag v-else size="small" type="success">当前活跃</el-tag>
    </div>
  </el-card>
</template>

<style scoped>
.source-card {
  width: 360px;
  flex-shrink: 0;
}

.source-card.active {
  border-color: #67c23a;
  box-shadow: 0 0 0 1px rgba(103, 194, 58, 0.2);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 10px;
}

.card-type {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-name {
  font-size: 15px;
  font-weight: 600;
}

.card-type-name {
  font-size: 12px;
  color: #909399;
}

.card-summary {
  font-size: 13px;
  color: #606266;
  font-family: monospace;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 12px;
  word-break: break-all;
}

.card-actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
</style>
