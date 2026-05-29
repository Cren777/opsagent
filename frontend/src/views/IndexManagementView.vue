<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { IndexStatus } from '@/types/indexes'
import {
  clearIndexCollection,
  fetchIndexStatus,
  rebuildCaseIndex,
  rebuildKnowledgeIndex,
  rebuildLogIndex,
} from '@/api/indexes'

const status = ref<IndexStatus | null>(null)
const loading = ref(false)
const action = ref('')

onMounted(loadStatus)

async function loadStatus() {
  loading.value = true
  try {
    const { data } = await fetchIndexStatus()
    status.value = data
  } finally {
    loading.value = false
  }
}

async function runAction(name: string, fn: () => Promise<unknown>) {
  action.value = name
  try {
    await fn()
    ElMessage.success('索引操作完成')
    await loadStatus()
  } finally {
    action.value = ''
  }
}
</script>

<template>
  <div class="ops-page">
    <div class="page-header">
      <div>
        <h2>索引管理</h2>
        <p class="page-desc">查看和维护知识库、日志与案例索引状态</p>
      </div>
      <el-button :icon="'Refresh'" @click="loadStatus">刷新</el-button>
    </div>

    <el-descriptions v-if="status" :column="1" border class="status-box">
      <el-descriptions-item label="Milvus DB">{{ status.milvus_db_path }}</el-descriptions-item>
      <el-descriptions-item label="知识目录">{{ status.knowledge_dir }}</el-descriptions-item>
      <el-descriptions-item label="日志目录">{{ status.log_dir }}</el-descriptions-item>
    </el-descriptions>

    <div class="actions">
      <el-button
        type="primary"
        :loading="action === 'knowledge'"
        @click="runAction('knowledge', rebuildKnowledgeIndex)"
      >
        重建知识索引
      </el-button>
      <el-button
        :loading="action === 'logs'"
        @click="runAction('logs', () => rebuildLogIndex())"
      >
        重建日志索引
      </el-button>
      <el-button
        :loading="action === 'cases'"
        @click="runAction('cases', rebuildCaseIndex)"
      >
        重建案例索引
      </el-button>
    </div>

    <el-table v-loading="loading" :data="status?.collections || []" border>
      <el-table-column prop="name" label="Collection" min-width="240" />
      <el-table-column prop="count" label="数量" width="120" />
      <el-table-column prop="status" label="状态" min-width="180" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-popconfirm title="确定清空此索引？" @confirm="runAction(row.name, () => clearIndexCollection(row.name))">
            <template #reference>
              <el-button size="small" text type="danger">清空</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.status-box {
  margin-bottom: 16px;
  overflow: hidden;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
</style>
