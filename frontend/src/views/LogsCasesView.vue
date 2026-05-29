<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { IncidentCaseItem, UploadedLogItem } from '@/types/incident'
import {
  deleteIncidentCase,
  deleteUploadedLog,
  fetchIncidentCase,
  fetchIncidentCases,
  fetchUploadedLogs,
  previewUploadedLog,
  updateIncidentCategory,
  updateIncidentStatus,
  updateUploadedLogCategory,
} from '@/api/incidents'

const activeTab = ref('logs')
const logs = ref<UploadedLogItem[]>([])
const cases = ref<IncidentCaseItem[]>([])
const loading = ref(false)
const previewVisible = ref(false)
const previewTitle = ref('')
const previewContent = ref('')

onMounted(loadAll)

async function loadAll() {
  loading.value = true
  try {
    const [logRes, caseRes] = await Promise.all([fetchUploadedLogs(), fetchIncidentCases()])
    logs.value = logRes.data
    cases.value = caseRes.data
  } finally {
    loading.value = false
  }
}

async function removeLog(row: UploadedLogItem) {
  await deleteUploadedLog(row.file_id)
  ElMessage.success('日志记录已删除')
  await loadAll()
}

async function previewLog(row: UploadedLogItem) {
  const { data } = await previewUploadedLog(row.file_id)
  previewTitle.value = data.filename
  previewContent.value = [
    `分类: ${data.category || '未分类'}`,
    `错误/警告: ${data.analysis.error_count} / ${data.analysis.warning_count}`,
    `关键模式: ${(data.analysis.patterns || []).join(', ') || '无'}`,
    '',
    data.content || data.analysis.summary || '无内容',
  ].join('\n')
  previewVisible.value = true
}

async function moveLog(row: UploadedLogItem) {
  const { value } = await ElMessageBox.prompt('请输入日志分类路径', '移动日志分类', {
    inputValue: row.category || '',
    inputPlaceholder: '例如 nginx/web-01',
  })
  await updateUploadedLogCategory(row.file_id, value || '')
  ElMessage.success('日志分类已更新')
  await loadAll()
}

async function setStatus(row: IncidentCaseItem, status: string) {
  await updateIncidentStatus(row.case_id, status)
  ElMessage.success('案例状态已更新')
  await loadAll()
}

async function previewCase(row: IncidentCaseItem) {
  const { data } = await fetchIncidentCase(row.case_id)
  previewTitle.value = data.query
  previewContent.value = [
    `分类: ${data.category || '未分类'}`,
    `状态: ${data.status}`,
    `症状: ${(data.symptoms || []).join(', ')}`,
    `根因: ${data.root_cause || '未记录'}`,
    `解决方案: ${data.solution || '未记录'}`,
    `证据: ${(data.evidence || []).join('; ') || '无'}`,
    '',
    data.answer,
  ].join('\n')
  previewVisible.value = true
}

async function moveCase(row: IncidentCaseItem) {
  const { value } = await ElMessageBox.prompt('请输入案例分类路径', '移动案例分类', {
    inputValue: row.category || '',
    inputPlaceholder: '例如 nginx/upstream',
  })
  await updateIncidentCategory(row.case_id, value || '')
  ElMessage.success('案例分类已更新')
  await loadAll()
}

async function removeCase(row: IncidentCaseItem) {
  await deleteIncidentCase(row.case_id)
  ElMessage.success('案例已删除')
  await loadAll()
}
</script>

<template>
  <div class="ops-page">
    <div class="page-header">
      <div>
        <h2>日志与案例</h2>
        <p class="page-desc">查看用户上传日志和自动沉淀的故障案例</p>
      </div>
      <el-button :icon="'Refresh'" @click="loadAll">刷新</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="上传日志" name="logs">
        <el-table v-loading="loading" :data="logs" border>
          <el-table-column prop="filename" label="文件名" min-width="220" />
          <el-table-column prop="size" label="大小" width="100" />
          <el-table-column prop="uploaded_at" label="上传时间" width="190" />
          <el-table-column prop="category" label="分类" width="160" />
          <el-table-column label="错误/警告" width="120">
            <template #default="{ row }">
              {{ row.analysis.error_count }} / {{ row.analysis.warning_count }}
            </template>
          </el-table-column>
          <el-table-column label="关键模式" min-width="220">
            <template #default="{ row }">
              <el-tag
                v-for="item in row.analysis.patterns"
                :key="item"
                size="small"
                class="tag"
                type="warning"
              >
                {{ item }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text @click="previewLog(row)">预览</el-button>
              <el-button size="small" text @click="moveLog(row)">分类</el-button>
              <el-popconfirm title="确定删除此日志？" @confirm="removeLog(row)">
                <template #reference>
                  <el-button size="small" text type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="故障案例" name="cases">
        <el-table v-loading="loading" :data="cases" border>
          <el-table-column prop="query" label="问题" min-width="240" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="分类" width="160" />
          <el-table-column label="症状" min-width="200">
            <template #default="{ row }">
              <el-tag v-for="item in row.symptoms" :key="item" size="small" class="tag">
                {{ item }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="190" />
          <el-table-column label="操作" width="300" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text @click="previewCase(row)">预览</el-button>
              <el-button size="small" text @click="moveCase(row)">分类</el-button>
              <el-button size="small" text @click="setStatus(row, 'resolved')">标记解决</el-button>
              <el-button size="small" text @click="setStatus(row, 'invalid')">无效</el-button>
              <el-popconfirm title="确定删除此案例？" @confirm="removeCase(row)">
                <template #reference>
                  <el-button size="small" text type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="previewVisible" :title="previewTitle" width="720px">
      <pre class="preview-content">{{ previewContent }}</pre>
    </el-dialog>
  </div>
</template>

<style scoped>
.tag {
  margin: 2px 4px 2px 0;
}

.preview-content {
  white-space: pre-wrap;
  word-break: break-word;
  background: #101828;
  color: #e4e7ec;
  border: 1px solid #1d2939;
  padding: 14px;
  line-height: 1.65;
  max-height: 60vh;
  overflow: auto;
}
</style>
