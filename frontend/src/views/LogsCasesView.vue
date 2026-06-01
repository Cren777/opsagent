<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { IncidentCaseItem, LogCategorySummary, UploadedLogItem } from '@/types/incident'
import {
  createIncidentCategory,
  createLogCategory,
  deleteIncidentCase,
  deleteIncidentCategory,
  deleteLogCategory,
  deleteUploadedLog,
  fetchIncidentCase,
  fetchIncidentCases,
  fetchIncidentCategories,
  fetchLogCategories,
  fetchUploadedLogs,
  pinIncidentCategory,
  pinLogCategory,
  previewUploadedLog,
  renameIncidentCategory,
  renameLogCategory,
  updateIncidentCategory,
  updateIncidentStatus,
  updateUploadedLogCategory,
} from '@/api/incidents'
import { uploadLogFile } from '@/api/upload'

const UNCATEGORIZED = '未分类'

const activeTab = ref<'logs' | 'cases'>('logs')
const logs = ref<UploadedLogItem[]>([])
const cases = ref<IncidentCaseItem[]>([])
const logCategories = ref<LogCategorySummary[]>([])
const caseCategories = ref<LogCategorySummary[]>([])
const loading = ref(false)
const uploadInputRef = ref<HTMLInputElement | null>(null)

const logQuery = ref('')
const logSource = ref('')
const logSeverity = ref('')
const selectedLogCategory = ref('')
const caseQuery = ref('')
const caseStatus = ref('')
const selectedCaseCategory = ref('')
const selectedSymptom = ref('')

const detailVisible = ref(false)
const detailTitle = ref('')
const detailMeta = ref<Record<string, string>>({})
const detailContent = ref('')

const categoryDialogVisible = ref(false)
const categoryTarget = ref<{ type: 'log' | 'case'; id: string; title: string } | null>(null)
const categoryValue = ref('')

const commonCategories = [
  'OpsAgent/运行日志',
  'Nginx/访问日志',
  'Nginx/错误日志',
  'MySQL/连接',
  '系统/权限',
  '系统/资源',
]

const logMetrics = computed(() => {
  const total = logs.value.length
  const errors = logs.value.reduce((sum, item) => sum + (item.analysis?.error_count || 0), 0)
  const warnings = logs.value.reduce((sum, item) => sum + (item.analysis?.warning_count || 0), 0)
  const uploaded = logs.value.filter((item) => item.source === 'uploaded').length
  return { total, errors, warnings, uploaded }
})

const unresolvedCases = computed(() =>
  cases.value.filter((item) => !['resolved', 'invalid'].includes(item.status)).length
)

const symptomOptions = computed(() => {
  const values = new Set<string>()
  for (const item of cases.value) {
    for (const symptom of item.symptoms || []) values.add(symptom)
  }
  return Array.from(values).sort()
})

const categoryOptions = computed(() => {
  const values = new Set(commonCategories)
  for (const item of logCategories.value) values.add(item.name)
  for (const item of caseCategories.value) values.add(item.name)
  values.delete(UNCATEGORIZED)
  return Array.from(values).filter(Boolean).sort()
})

onMounted(loadAll)

async function loadAll() {
  loading.value = true
  try {
    const [logRes, logCategoryRes, caseRes, caseCategoryRes] = await Promise.all([
      fetchUploadedLogs({
        query: logQuery.value || undefined,
        category: selectedLogCategory.value || undefined,
        source: logSource.value || undefined,
        severity: logSeverity.value || undefined,
      }),
      fetchLogCategories(),
      fetchIncidentCases({
        query: caseQuery.value || undefined,
        category: selectedCaseCategory.value || undefined,
        status: caseStatus.value || undefined,
        symptom: selectedSymptom.value || undefined,
      }),
      fetchIncidentCategories(),
    ])
    logs.value = logRes.data
    logCategories.value = logCategoryRes.data
    cases.value = caseRes.data
    caseCategories.value = caseCategoryRes.data
  } finally {
    loading.value = false
  }
}

function resetLogFilters() {
  logQuery.value = ''
  logSource.value = ''
  logSeverity.value = ''
  selectedLogCategory.value = ''
  loadAll()
}

function resetCaseFilters() {
  caseQuery.value = ''
  caseStatus.value = ''
  selectedCaseCategory.value = ''
  selectedSymptom.value = ''
  loadAll()
}

function selectLogCategory(name: string) {
  selectedLogCategory.value = name === UNCATEGORIZED ? '' : name
  activeTab.value = 'logs'
  loadAll()
}

function selectCaseCategory(name: string) {
  selectedCaseCategory.value = name === UNCATEGORIZED ? '' : name
  activeTab.value = 'cases'
  loadAll()
}

function openUploadPicker() {
  uploadInputRef.value?.click()
}

async function onUploadChange(event: Event) {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])
  target.value = ''
  if (!files.length) return

  loading.value = true
  try {
    for (const file of files) {
      await uploadLogFile(file, { category: selectedLogCategory.value })
    }
    ElMessage.success('日志已上传')
    await loadAll()
  } finally {
    loading.value = false
  }
}

async function previewLog(row: UploadedLogItem) {
  const { data } = await previewUploadedLog(row.file_id)
  detailTitle.value = data.filename
  detailMeta.value = {
    来源: sourceLabel(data.source),
    分类: data.category || UNCATEGORIZED,
    严重度: severityLabel(data.severity),
    '错误/警告': `${data.analysis.error_count} / ${data.analysis.warning_count}`,
    路径: data.stored_path || '',
  }
  detailContent.value = data.content || data.analysis.summary || '暂无内容'
  detailVisible.value = true
}

async function previewCase(row: IncidentCaseItem) {
  const { data } = await fetchIncidentCase(row.case_id)
  detailTitle.value = data.query
  detailMeta.value = {
    状态: statusLabel(data.status),
    分类: data.category || UNCATEGORIZED,
    症状: (data.symptoms || []).join(', ') || '无',
    根因: data.root_cause || '未记录',
    方案: data.solution || '未记录',
  }
  detailContent.value = data.answer || '暂无内容'
  detailVisible.value = true
}

function openCategoryDialog(type: 'log' | 'case', row: UploadedLogItem | IncidentCaseItem) {
  categoryTarget.value = {
    type,
    id: type === 'log' ? (row as UploadedLogItem).file_id : (row as IncidentCaseItem).case_id,
    title: type === 'log' ? (row as UploadedLogItem).filename : (row as IncidentCaseItem).query,
  }
  categoryValue.value = row.category || ''
  categoryDialogVisible.value = true
}

async function saveCategory() {
  if (!categoryTarget.value) return
  if (categoryTarget.value.type === 'log') {
    await updateUploadedLogCategory(categoryTarget.value.id, categoryValue.value)
  } else {
    await updateIncidentCategory(categoryTarget.value.id, categoryValue.value)
  }
  categoryDialogVisible.value = false
  ElMessage.success('分类已更新')
  await loadAll()
}

async function createCategory(type: 'log' | 'case') {
  const { value } = await ElMessageBox.prompt('输入分类名称，可使用 / 创建层级', '新建分类', {
    inputPlaceholder: '例如 MySQL/连接池',
  })
  if (!value) return
  if (type === 'log') {
    await createLogCategory(value)
  } else {
    await createIncidentCategory(value)
  }
  ElMessage.success('分类已创建')
  await loadAll()
}

async function renameCategory(type: 'log' | 'case', item: LogCategorySummary) {
  const { value } = await ElMessageBox.prompt('输入新的分类名称', '重命名分类', {
    inputValue: item.name,
  })
  if (!value || value === item.name) return
  if (type === 'log') {
    await renameLogCategory(item.name, value)
    if (selectedLogCategory.value === item.name) selectedLogCategory.value = value
  } else {
    await renameIncidentCategory(item.name, value)
    if (selectedCaseCategory.value === item.name) selectedCaseCategory.value = value
  }
  ElMessage.success('分类已重命名，已有内容已同步')
  await loadAll()
}

async function togglePinCategory(type: 'log' | 'case', item: LogCategorySummary) {
  if (type === 'log') {
    await pinLogCategory(item.name, !item.pinned)
  } else {
    await pinIncidentCategory(item.name, !item.pinned)
  }
  await loadAll()
}

async function removeCategory(type: 'log' | 'case', item: LogCategorySummary) {
  await ElMessageBox.confirm(
    `删除分类“${item.name}”后，已有内容会移动到未分类。是否继续？`,
    '删除分类',
    { type: 'warning' }
  )
  if (type === 'log') {
    await deleteLogCategory(item.name)
    if (selectedLogCategory.value === item.name) selectedLogCategory.value = ''
  } else {
    await deleteIncidentCategory(item.name)
    if (selectedCaseCategory.value === item.name) selectedCaseCategory.value = ''
  }
  ElMessage.success('分类已删除')
  await loadAll()
}

async function removeLog(row: UploadedLogItem) {
  await ElMessageBox.confirm(`确定删除日志记录 ${row.filename}？`, '删除日志', { type: 'warning' })
  await deleteUploadedLog(row.file_id)
  ElMessage.success('日志记录已删除')
  await loadAll()
}

async function removeCase(row: IncidentCaseItem) {
  await ElMessageBox.confirm('确定删除该故障案例？', '删除案例', { type: 'warning' })
  await deleteIncidentCase(row.case_id)
  ElMessage.success('案例已删除')
  await loadAll()
}

async function setStatus(row: IncidentCaseItem, status: string) {
  await updateIncidentStatus(row.case_id, status)
  ElMessage.success('案例状态已更新')
  await loadAll()
}

function sourceLabel(source?: string) {
  const map: Record<string, string> = {
    uploaded: '上传日志',
    runtime: '运行日志',
    seed: '样例日志',
    local: '本地日志',
  }
  return map[source || ''] || '未知来源'
}

function severityLabel(severity?: string) {
  const map: Record<string, string> = {
    error: '错误',
    warning: '警告',
    info: '普通',
  }
  return map[severity || ''] || '普通'
}

function severityType(severity?: string) {
  if (severity === 'error') return 'danger'
  if (severity === 'warning') return 'warning'
  return 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    auto_saved: '待整理',
    triaged: '已分诊',
    resolved: '已解决',
    invalid: '无效',
  }
  return map[status] || status
}

function statusType(status: string) {
  if (status === 'resolved') return 'success'
  if (status === 'invalid') return 'info'
  if (status === 'triaged') return 'warning'
  return 'primary'
}

function formatSize(size: number) {
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${size || 0} B`
}

function formatTime(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}
</script>

<template>
  <div class="ops-page logs-cases-page">
    <div class="page-header">
      <div>
        <h2>日志与案例</h2>
        <p class="page-desc">按分类管理运行日志、上传日志和故障案例</p>
      </div>
      <div class="header-actions">
        <input ref="uploadInputRef" class="hidden-input" type="file" accept=".log,.txt,.out,.gz" multiple @change="onUploadChange" />
        <el-button :icon="'Upload'" type="primary" @click="openUploadPicker">上传日志</el-button>
        <el-button :icon="'Refresh'" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <div class="metric-row">
      <div class="metric-item"><span>日志文件</span><strong>{{ logMetrics.total }}</strong></div>
      <div class="metric-item danger"><span>错误</span><strong>{{ logMetrics.errors }}</strong></div>
      <div class="metric-item warning"><span>警告</span><strong>{{ logMetrics.warnings }}</strong></div>
      <div class="metric-item"><span>上传日志</span><strong>{{ logMetrics.uploaded }}</strong></div>
      <div class="metric-item"><span>待整理案例</span><strong>{{ unresolvedCases }}</strong></div>
    </div>

    <div class="workspace">
      <aside class="filter-rail">
        <div class="rail-section">
          <div class="rail-header">
            <span>日志分类</span>
            <el-button :icon="'Plus'" circle size="small" text @click="createCategory('log')" />
          </div>
          <button class="rail-item" :class="{ active: activeTab === 'logs' && !selectedLogCategory }" @click="selectLogCategory(UNCATEGORIZED)">
            <span>全部日志</span><b>{{ logMetrics.total }}</b>
          </button>
          <div v-for="item in logCategories" :key="item.name" class="rail-row" :class="{ active: activeTab === 'logs' && selectedLogCategory === item.name }">
            <button class="rail-item category-button" @click="selectLogCategory(item.name)">
              <span><i v-if="item.pinned">★</i>{{ item.name }}</span><b>{{ item.count }}</b>
            </button>
            <el-dropdown trigger="click" @command="(cmd: string) => cmd === 'rename' ? renameCategory('log', item) : cmd === 'pin' ? togglePinCategory('log', item) : removeCategory('log', item)">
              <el-button :icon="'MoreFilled'" text circle size="small" />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">重命名</el-dropdown-item>
                  <el-dropdown-item command="pin">{{ item.pinned ? '取消置顶' : '置顶' }}</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <div class="rail-section">
          <div class="rail-header">
            <span>案例分类</span>
            <el-button :icon="'Plus'" circle size="small" text @click="createCategory('case')" />
          </div>
          <button class="rail-item" :class="{ active: activeTab === 'cases' && !selectedCaseCategory }" @click="selectCaseCategory(UNCATEGORIZED)">
            <span>全部案例</span><b>{{ cases.length }}</b>
          </button>
          <div v-for="item in caseCategories" :key="item.name" class="rail-row" :class="{ active: activeTab === 'cases' && selectedCaseCategory === item.name }">
            <button class="rail-item category-button" @click="selectCaseCategory(item.name)">
              <span><i v-if="item.pinned">★</i>{{ item.name }}</span><b>{{ item.count }}</b>
            </button>
            <el-dropdown trigger="click" @command="(cmd: string) => cmd === 'rename' ? renameCategory('case', item) : cmd === 'pin' ? togglePinCategory('case', item) : removeCategory('case', item)">
              <el-button :icon="'MoreFilled'" text circle size="small" />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">重命名</el-dropdown-item>
                  <el-dropdown-item command="pin">{{ item.pinned ? '取消置顶' : '置顶' }}</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </aside>

      <main class="content-panel">
        <el-tabs v-model="activeTab" class="workspace-tabs">
          <el-tab-pane label="日志文件" name="logs">
            <div class="toolbar">
              <el-input v-model="logQuery" :prefix-icon="'Search'" placeholder="搜索文件名、分类、关键模式" clearable class="search-input" @keyup.enter="loadAll" @clear="loadAll" />
              <el-radio-group v-model="logSource" @change="loadAll">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="runtime">运行日志</el-radio-button>
                <el-radio-button label="uploaded">上传日志</el-radio-button>
                <el-radio-button label="seed">样例日志</el-radio-button>
              </el-radio-group>
              <el-select v-model="logSeverity" placeholder="严重度" clearable class="filter-select" @change="loadAll">
                <el-option label="错误" value="error" />
                <el-option label="警告" value="warning" />
                <el-option label="普通" value="info" />
              </el-select>
              <el-button :icon="'Search'" type="primary" plain @click="loadAll">筛选</el-button>
              <el-button text @click="resetLogFilters">重置</el-button>
            </div>

            <el-table v-loading="loading" :data="logs" class="data-table" height="calc(100vh - 350px)">
              <el-table-column prop="filename" label="文件名" min-width="230" show-overflow-tooltip />
              <el-table-column label="来源" width="100"><template #default="{ row }"><el-tag size="small" effect="plain">{{ sourceLabel(row.source) }}</el-tag></template></el-table-column>
              <el-table-column label="分类" min-width="160" show-overflow-tooltip><template #default="{ row }">{{ row.category || UNCATEGORIZED }}</template></el-table-column>
              <el-table-column label="严重度" width="90"><template #default="{ row }"><el-tag size="small" :type="severityType(row.severity)">{{ severityLabel(row.severity) }}</el-tag></template></el-table-column>
              <el-table-column label="错误/警告" width="110"><template #default="{ row }">{{ row.analysis.error_count }} / {{ row.analysis.warning_count }}</template></el-table-column>
              <el-table-column label="关键模式" min-width="180">
                <template #default="{ row }">
                  <el-tag v-for="tag in row.analysis.patterns" :key="tag" size="small" class="tag" type="warning" effect="plain">{{ tag }}</el-tag>
                  <span v-if="!row.analysis.patterns?.length" class="muted">无</span>
                </template>
              </el-table-column>
              <el-table-column label="大小" width="100"><template #default="{ row }">{{ formatSize(row.size) }}</template></el-table-column>
              <el-table-column label="更新时间" width="180"><template #default="{ row }">{{ formatTime(row.updated_at || row.uploaded_at) }}</template></el-table-column>
              <el-table-column label="操作" width="210" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" text @click="previewLog(row)">预览</el-button>
                  <el-button size="small" text @click="openCategoryDialog('log', row)">分类</el-button>
                  <el-button size="small" text type="danger" @click="removeLog(row)">删除</el-button>
                </template>
              </el-table-column>
              <template #empty><el-empty description="未找到日志。可上传日志，或检查 logs/ 与 data/logs/ 目录。" /></template>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="故障案例" name="cases">
            <div class="toolbar">
              <el-input v-model="caseQuery" :prefix-icon="'Search'" placeholder="搜索问题、方案、症状" clearable class="search-input" @keyup.enter="loadAll" @clear="loadAll" />
              <el-radio-group v-model="caseStatus" @change="loadAll">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="auto_saved">待整理</el-radio-button>
                <el-radio-button label="resolved">已解决</el-radio-button>
                <el-radio-button label="invalid">无效</el-radio-button>
              </el-radio-group>
              <el-select v-model="selectedSymptom" placeholder="症状标签" clearable class="filter-select" @change="loadAll">
                <el-option v-for="item in symptomOptions" :key="item" :label="item" :value="item" />
              </el-select>
              <el-button :icon="'Search'" type="primary" plain @click="loadAll">筛选</el-button>
              <el-button text @click="resetCaseFilters">重置</el-button>
            </div>

            <el-table v-loading="loading" :data="cases" class="data-table" height="calc(100vh - 350px)">
              <el-table-column prop="query" label="问题摘要" min-width="260" show-overflow-tooltip />
              <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag size="small" :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
              <el-table-column label="分类" min-width="150" show-overflow-tooltip><template #default="{ row }">{{ row.category || UNCATEGORIZED }}</template></el-table-column>
              <el-table-column label="症状标签" min-width="220"><template #default="{ row }"><el-tag v-for="tag in row.symptoms" :key="tag" size="small" class="tag" effect="plain">{{ tag }}</el-tag></template></el-table-column>
              <el-table-column label="命中证据" min-width="180" show-overflow-tooltip><template #default="{ row }">{{ (row.evidence || []).join('；') || '无' }}</template></el-table-column>
              <el-table-column label="更新时间" width="180"><template #default="{ row }">{{ formatTime(row.updated_at) }}</template></el-table-column>
              <el-table-column label="操作" width="280" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" text @click="previewCase(row)">预览</el-button>
                  <el-button size="small" text @click="openCategoryDialog('case', row)">分类</el-button>
                  <el-button size="small" text @click="setStatus(row, 'resolved')">已解决</el-button>
                  <el-button size="small" text @click="setStatus(row, 'invalid')">无效</el-button>
                  <el-button size="small" text type="danger" @click="removeCase(row)">删除</el-button>
                </template>
              </el-table-column>
              <template #empty><el-empty description="暂无故障案例。完成一次故障排查后会自动沉淀到这里。" /></template>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </main>
    </div>

    <el-drawer v-model="detailVisible" :title="detailTitle" size="46%">
      <div class="detail-meta">
        <div v-for="(value, key) in detailMeta" :key="key" class="detail-meta-item">
          <span>{{ key }}</span>
          <strong>{{ value || '-' }}</strong>
        </div>
      </div>
      <pre class="preview-content">{{ detailContent }}</pre>
    </el-drawer>

    <el-dialog v-model="categoryDialogVisible" title="调整分类" width="480px">
      <div class="category-form">
        <div class="target-title">{{ categoryTarget?.title }}</div>
        <el-select v-model="categoryValue" filterable allow-create default-first-option clearable placeholder="选择或输入分类路径" class="category-select">
          <el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <p class="category-preview">最终分类：{{ categoryValue || UNCATEGORIZED }}</p>
      </div>
      <template #footer>
        <el-button @click="categoryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCategory">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.logs-cases-page { display: flex; flex-direction: column; gap: 16px; min-height: 100%; }
.page-header, .header-actions, .toolbar, .metric-row, .workspace { display: flex; align-items: center; }
.header-actions { gap: 10px; }
.hidden-input { display: none; }
.metric-row { gap: 12px; flex-wrap: wrap; }
.metric-item { min-width: 138px; padding: 12px 14px; border: 1px solid var(--ops-border); background: rgba(255,255,255,.78); border-radius: 8px; }
.metric-item span { display: block; color: var(--ops-text-muted); font-size: 12px; margin-bottom: 4px; }
.metric-item strong { color: var(--ops-text); font-size: 24px; line-height: 1; }
.metric-item.danger strong { color: #d92d20; }
.metric-item.warning strong { color: #b54708; }
.workspace { align-items: stretch; gap: 16px; min-height: 0; }
.filter-rail { width: 260px; flex-shrink: 0; border-right: 1px solid var(--ops-border-soft); padding-right: 14px; }
.rail-section + .rail-section { margin-top: 22px; }
.rail-header { display: flex; align-items: center; justify-content: space-between; color: var(--ops-text-muted); font-size: 12px; font-weight: 700; margin-bottom: 8px; }
.rail-row { display: grid; grid-template-columns: 1fr 30px; align-items: center; border-radius: 6px; }
.rail-row:hover, .rail-row.active { background: var(--ops-primary-soft); }
.rail-item { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 8px; border: 0; background: transparent; color: var(--ops-text-secondary); border-radius: 6px; padding: 8px 10px; cursor: pointer; text-align: left; }
.rail-item span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rail-item i { color: #f59e0b; font-style: normal; margin-right: 4px; }
.rail-item b { color: var(--ops-text-muted); font-size: 12px; }
.rail-item:hover, .rail-item.active, .rail-row.active .rail-item { color: var(--ops-primary); }
.category-button { border-radius: 6px 0 0 6px; }
.content-panel { flex: 1; min-width: 0; }
.workspace-tabs :deep(.el-tabs__header) { margin-bottom: 12px; }
.toolbar { gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.search-input { width: 280px; }
.filter-select { width: 150px; }
.data-table { border: 1px solid var(--ops-border-soft); border-radius: 8px; overflow: hidden; }
.tag { margin: 2px 4px 2px 0; }
.muted { color: var(--ops-text-muted); }
.detail-meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
.detail-meta-item { border: 1px solid var(--ops-border-soft); border-radius: 6px; padding: 10px; background: var(--ops-surface-muted); }
.detail-meta-item span { display: block; color: var(--ops-text-muted); font-size: 12px; margin-bottom: 4px; }
.detail-meta-item strong { color: var(--ops-text); font-size: 13px; word-break: break-word; }
.preview-content { white-space: pre-wrap; word-break: break-word; background: #111827; color: #e5e7eb; border: 1px solid #1f2937; border-radius: 8px; padding: 14px; line-height: 1.65; max-height: 62vh; overflow: auto; }
.category-form { display: flex; flex-direction: column; gap: 12px; }
.target-title { color: var(--ops-text-secondary); line-height: 1.5; word-break: break-word; }
.category-select { width: 100%; }
.category-preview { color: var(--ops-text-muted); margin: 0; }
@media (max-width: 1100px) {
  .workspace { flex-direction: column; }
  .filter-rail { width: 100%; border-right: 0; border-bottom: 1px solid var(--ops-border-soft); padding-right: 0; padding-bottom: 12px; }
}
</style>
