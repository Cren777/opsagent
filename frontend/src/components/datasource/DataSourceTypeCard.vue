<script setup lang="ts">
import type { DataSourceItem } from '@/types/datasource'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const props = defineProps<{ source: DataSourceItem; testing?: boolean }>()
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
  if (source.type === 'excel_csv') {
    const files = c.files as Array<{ original_filename?: string; file_path?: string }> | undefined
    if (files && files.length > 0) {
      const first = files[0].original_filename || files[0].file_path || ''
      return files.length === 1 ? first : `${first} 等 ${files.length} 个文件`
    }
    return (c.original_filename as string) || (c.file_path as string) || ''
  }
  return `${c.host || ''}:${c.port || ''}/${c.database || ''}`
}

function getSelectedTables(source: DataSourceItem): string[] {
  if (source.type === 'excel_csv') return []
  const c = source.config as unknown as Record<string, unknown>
  const tables = c.selected_tables as string[] | undefined
  return tables || []
}

function getTableCount(source: DataSourceItem): { selected: number; total: number } {
  const c = source.config as unknown as Record<string, unknown>
  const allTables = c.all_tables as string[] | undefined
  const total = (c.total_tables as number) || allTables?.length || 0
  const selected = getSelectedTables(source).length
  return { selected, total }
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

    <div v-if="getTableCount(source).total > 0" class="card-tables">
      <div class="table-count-badge">
        <el-icon :size="14"><Grid /></el-icon>
        <span>{{ getTableCount(source).selected }}/{{ getTableCount(source).total }}</span>
      </div>
    </div>

    <div class="card-actions">
      <el-button size="small" text :icon="'Connection'" :loading="testing" @click="emit('test', source.id)">测试</el-button>
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
  width: 100%;
  min-height: 178px;
  border: 1px solid var(--ops-border);
  border-radius: var(--ops-radius);
}

.source-card.active {
  border-color: rgba(24, 160, 88, 0.55);
  box-shadow: 0 0 0 3px rgba(24, 160, 88, 0.1);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.card-type {
  display: flex;
  align-items: center;
  gap: 11px;
}

.card-name {
  font-size: 15px;
  font-weight: 800;
  color: var(--ops-text);
}

.card-type-name {
  font-size: 12px;
  color: var(--ops-text-muted);
}

.card-summary {
  font-size: 13px;
  color: var(--ops-text-secondary);
  font-family: var(--ops-font-mono);
  padding: 9px 10px;
  background: var(--ops-surface-muted);
  border: 1px solid var(--ops-border-soft);
  border-radius: 7px;
  margin-bottom: 10px;
  word-break: break-all;
}

.card-tables {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.table-count-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  background: var(--ops-primary-soft);
  border-radius: 5px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ops-primary-strong);
  flex-shrink: 0;
}

.card-actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
</style>
