<script setup lang="ts">
import { ref, reactive, watch, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import type {
  DataSourceFormData,
  ConnectionTestResult,
  ExcelCSVConfig,
  ExcelCSVFileConfig,
} from '@/types/datasource'
import { useConfigStore } from '@/stores/config'
import { fetchNewTables, uploadExcelCsvFile } from '@/api/datasource'

const MAX_EXCEL_CSV_FILES = 5

const props = defineProps<{ sourceId?: string }>()
const emit = defineEmits<{ saved: [] }>()

const configStore = useConfigStore()
const visible = ref(false)
const saving = ref(false)
const testing = ref(false)
const uploadingFile = ref(false)
const testResult = ref<ConnectionTestResult | null>(null)
const tables = ref<string[]>([])
const selectedTables = ref<string[]>([])
const fetchingTables = ref(false)
const connectionTested = ref(false)
const savedTotalTables = ref(0)
const editingSourceId = ref<string | undefined>()
const initializing = ref(false)

const form = reactive<DataSourceFormData>({
  name: '',
  type: 'mysql',
  config: { host: '', port: 3306, user: '', password: '', database: '', charset: 'utf8mb4' },
})

const excelCsvConfig = computed(() => form.config as ExcelCSVConfig)
const excelCsvFiles = computed<ExcelCSVFileConfig[]>(() => excelCsvConfig.value.files || [])

const isIndeterminate = computed(() => {
  return selectedTables.value.length > 0 && selectedTables.value.length < tables.value.length
})

const checkAll = computed(() => {
  return tables.value.length > 0 && selectedTables.value.length === tables.value.length
})

const readonlyTables = computed(() => {
  return tables.value.length > 0 ? tables.value : selectedTables.value
})

const canTest = computed(() => {
  if (form.type === 'excel_csv') return excelCsvFiles.value.length > 0 && !uploadingFile.value
  const c = form.config as { host: string; database: string }
  return !!c.host && !!c.database
})

const canSave = computed(() => {
  if (!form.name.trim()) return false
  if (form.type === 'excel_csv') return excelCsvFiles.value.length > 0 && !uploadingFile.value
  return true
})

async function open(source?: DataSourceFormData & { id?: string }) {
  initializing.value = true
  editingSourceId.value = source?.id
  testResult.value = null
  tables.value = []
  selectedTables.value = []
  connectionTested.value = false
  savedTotalTables.value = 0
  uploadingFile.value = false

  if (source) {
    form.name = source.name
    form.type = source.type
    form.config = normalizeExcelCsvConfig(JSON.parse(JSON.stringify(source.config)), source.type)
    const config = source.config as unknown as Record<string, unknown>
    const saved = config.selected_tables as string[] | undefined
    if (saved && saved.length > 0) selectedTables.value = [...saved]

    savedTotalTables.value = (config.total_tables as number) || 0
    const allTables = config.all_tables as string[] | undefined
    if (allTables && allTables.length > 0) {
      tables.value = [...allTables]
    } else if (selectedTables.value.length > 0 && form.type !== 'excel_csv') {
      fetchTableList(selectedTables.value)
    }
  } else {
    form.name = ''
    form.type = 'mysql'
    resetConfig()
  }

  await nextTick()
  initializing.value = false
  visible.value = true
}

function normalizeExcelCsvConfig(config: unknown, type: string) {
  if (type !== 'excel_csv') return config as DataSourceFormData['config']
  const c = config as ExcelCSVConfig
  if (c.files && c.files.length > 0) return c
  if (c.file_path) {
    c.files = [{
      file_path: c.file_path,
      sheet_name: c.sheet_name,
      upload_id: c.upload_id,
      original_filename: c.original_filename,
      file_type: c.file_type,
      sheet_names: c.sheet_names,
    }]
  } else {
    c.files = []
  }
  return c
}

function resetConfig() {
  if (form.type === 'mysql') {
    form.config = { host: '', port: 3306, user: '', password: '', database: '', charset: 'utf8mb4' }
  } else if (form.type === 'clickhouse') {
    form.config = { host: '', port: 8123, user: '', password: '', database: '' }
  } else {
    form.config = { file_path: '', sheet_name: '', files: [] }
  }
}

watch(() => form.type, () => {
  if (initializing.value) return
  resetConfig()
  testResult.value = null
  tables.value = []
  selectedTables.value = []
  connectionTested.value = false
  savedTotalTables.value = 0
})

function handleCheckAllChange(val: boolean) {
  selectedTables.value = val ? [...tables.value] : []
}

async function handleExcelCsvFileChange(uploadFile: { raw?: File }) {
  const file = uploadFile.raw
  if (!file) return
  if (excelCsvFiles.value.length >= MAX_EXCEL_CSV_FILES) {
    ElMessage.warning(`最多只能上传 ${MAX_EXCEL_CSV_FILES} 个文件`)
    return
  }

  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ext || !['csv', 'xlsx', 'xls'].includes(ext)) {
    ElMessage.error('仅支持上传 .csv、.xlsx、.xls 文件')
    return
  }

  uploadingFile.value = true
  testResult.value = null
  connectionTested.value = false
  try {
    const { data } = await uploadExcelCsvFile(file)
    const nextFile: ExcelCSVFileConfig = {
      file_path: data.file_path,
      sheet_name: data.sheet_names[0] || '',
      upload_id: data.upload_id,
      original_filename: data.original_filename,
      file_type: data.file_type,
      sheet_names: data.sheet_names,
      size_bytes: data.size_bytes,
    }
    const files = [...excelCsvFiles.value, nextFile]
    form.config = toExcelCsvConfig(files)
    if (!form.name.trim()) form.name = fileStem(data.original_filename)
    ElMessage.success('文件上传成功')
  } catch {
    // API interceptor already shows the backend error.
  } finally {
    uploadingFile.value = false
  }
}

function handleExcelCsvExceed() {
  ElMessage.warning(`最多只能上传 ${MAX_EXCEL_CSV_FILES} 个文件`)
}

function removeExcelCsvFile(index: number) {
  const files = excelCsvFiles.value.filter((_, i) => i !== index)
  form.config = toExcelCsvConfig(files)
  testResult.value = null
  connectionTested.value = false
}

function updateExcelCsvSheet(index: number, sheetName: string) {
  const files = excelCsvFiles.value.map((file, i) => (
    i === index ? { ...file, sheet_name: sheetName } : file
  ))
  form.config = toExcelCsvConfig(files)
  testResult.value = null
  connectionTested.value = false
}

function toExcelCsvConfig(files: ExcelCSVFileConfig[]): ExcelCSVConfig {
  const first = files[0]
  return {
    file_path: first?.file_path || '',
    sheet_name: first?.sheet_name || '',
    upload_id: first?.upload_id,
    original_filename: first?.original_filename,
    file_type: first?.file_type,
    sheet_names: first?.sheet_names,
    files,
  }
}

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请先填写数据源名称')
    return
  }
  if (form.type === 'excel_csv' && excelCsvFiles.value.length === 0) {
    ElMessage.warning('请先上传 Excel/CSV 文件')
    return
  }

  saving.value = true
  try {
    const payload = JSON.parse(JSON.stringify(form))
    payload.name = payload.name.trim()
    if (form.type !== 'excel_csv') {
      payload.config.selected_tables = selectedTables.value
      payload.config.all_tables = tables.value
    }
    if (tables.value.length > 0) {
      payload.config.total_tables = tables.value.length
    } else if (savedTotalTables.value > 0) {
      payload.config.total_tables = savedTotalTables.value
    }
    await configStore.saveDataSource(payload, editingSourceId.value || props.sourceId)
    ElMessage.success('保存成功')
    visible.value = false
    emit('saved')
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null
  const oldSelection = [...selectedTables.value]
  try {
    const result = await configStore.testNewConnection(JSON.parse(JSON.stringify(form)))
    testResult.value = result
    ElMessage[result.ok ? 'success' : 'error'](result.message)
    if (result.ok) {
      connectionTested.value = true
      if (form.type !== 'excel_csv') await fetchTableList(oldSelection)
    }
  } catch (e: unknown) {
    testResult.value = { ok: false, message: (e as Error).message || '测试失败' }
    ElMessage.error('测试失败')
  } finally {
    testing.value = false
  }
}

async function fetchTableList(oldSelection: string[] = []) {
  fetchingTables.value = true
  tables.value = []
  try {
    const { data } = await fetchNewTables(JSON.parse(JSON.stringify(form)))
    tables.value = data.tables || []
    if (oldSelection.length > 0) {
      selectedTables.value = oldSelection.filter((t) => tables.value.includes(t))
    } else {
      selectedTables.value = []
    }
  } catch {
    // 获取表列表失败不阻塞用户继续编辑配置。
  } finally {
    fetchingTables.value = false
  }
}

function fileStem(filename = '') {
  return filename.replace(/\.[^.]+$/, '') || 'Excel/CSV 数据源'
}

function formatFileSize(size?: number) {
  if (!size) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

defineExpose({ open })
</script>

<template>
  <el-drawer
    v-model="visible"
    :title="editingSourceId ? '编辑数据源' : '添加数据源'"
    size="480px"
    destroy-on-close
  >
    <el-form label-position="top" size="default">
      <el-form-item label="数据源名称" required>
        <el-input v-model="form.name" placeholder="例如：生产环境 MySQL" />
      </el-form-item>

      <el-form-item label="数据源类型" required>
        <el-radio-group v-model="form.type">
          <el-radio-button value="mysql">
            <el-icon><DataBoard /></el-icon> MySQL
          </el-radio-button>
          <el-radio-button value="clickhouse">
            <el-icon><DataAnalysis /></el-icon> ClickHouse
          </el-radio-button>
          <el-radio-button value="excel_csv">
            <el-icon><Document /></el-icon> Excel/CSV
          </el-radio-button>
        </el-radio-group>
      </el-form-item>

      <template v-if="form.type === 'mysql' || form.type === 'clickhouse'">
        <el-row :gutter="16">
          <el-col :span="16">
            <el-form-item label="主机地址" required>
              <el-input v-model="(form.config as { host: string }).host" placeholder="127.0.0.1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="端口" required>
              <el-input-number
                v-model="(form.config as { port: number }).port"
                :min="1"
                :max="65535"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用户名" required>
              <el-input v-model="(form.config as { user: string }).user" placeholder="root" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码">
              <el-input
                v-model="(form.config as { password: string }).password"
                type="password"
                show-password
                placeholder="请输入密码"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="数据库名" required>
          <el-input v-model="(form.config as { database: string }).database" placeholder="ops_agent" />
        </el-form-item>

        <el-form-item v-if="form.type === 'mysql'" label="字符集">
          <el-select v-model="(form.config as { charset: string }).charset" style="width: 100%">
            <el-option label="utf8mb4 (推荐)" value="utf8mb4" />
            <el-option label="utf8" value="utf8" />
            <el-option label="latin1" value="latin1" />
          </el-select>
        </el-form-item>
      </template>

      <template v-else>
        <el-form-item label="上传文件" required>
          <el-upload
            class="file-upload"
            drag
            multiple
            accept=".csv,.xlsx,.xls"
            :limit="MAX_EXCEL_CSV_FILES"
            :auto-upload="false"
            :show-file-list="false"
            :disabled="uploadingFile || excelCsvFiles.length >= MAX_EXCEL_CSV_FILES"
            :on-change="handleExcelCsvFileChange"
            :on-exceed="handleExcelCsvExceed"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">点击或拖拽上传 Excel/CSV 文件</div>
            <template #tip>
              <div class="form-hint">
                仅支持 .csv、.xlsx、.xls，最多上传 {{ MAX_EXCEL_CSV_FILES }} 个文件。
              </div>
            </template>
          </el-upload>

          <div v-if="uploadingFile" class="upload-status">
            <el-icon class="is-loading"><Loading /></el-icon>
            正在上传文件...
          </div>

          <div v-if="excelCsvFiles.length > 0" class="file-list">
            <div v-for="(file, index) in excelCsvFiles" :key="file.upload_id || file.file_path" class="file-row">
              <div class="file-main">
                <el-icon><Document /></el-icon>
                <div class="file-meta">
                  <div class="file-name">{{ file.original_filename || file.file_path }}</div>
                  <div class="file-sub">
                    {{ file.file_type?.toUpperCase() || 'FILE' }}
                    <span v-if="formatFileSize(file.size_bytes)"> · {{ formatFileSize(file.size_bytes) }}</span>
                  </div>
                </div>
                <el-tag size="small" type="success" effect="plain">已上传</el-tag>
                <el-button text type="danger" :icon="'Delete'" @click="removeExcelCsvFile(index)" />
              </div>

              <el-select
                v-if="file.sheet_names && file.sheet_names.length > 0"
                :model-value="file.sheet_name"
                placeholder="请选择工作表"
                size="small"
                class="sheet-select"
                @update:model-value="(value: string) => updateExcelCsvSheet(index, value)"
              >
                <el-option
                  v-for="sheet in file.sheet_names"
                  :key="sheet"
                  :label="sheet"
                  :value="sheet"
                />
              </el-select>
            </div>
          </div>
        </el-form-item>
      </template>

      <div v-if="testResult" class="test-result">
        <el-alert
          :title="testResult.ok ? '连接成功' : '连接失败'"
          :description="testResult.message + (testResult.latency_ms ? ` (延迟: ${testResult.latency_ms}ms)` : '')"
          :type="testResult.ok ? 'success' : 'error'"
          show-icon
          closable
        />
      </div>

      <div v-if="!connectionTested && readonlyTables.length > 0 && form.type !== 'excel_csv'" class="table-section">
        <el-divider />
        <div class="section-label">已选择的表（测试连接后可修改）</div>
        <div class="table-checkbox-group">
          <el-checkbox
            v-for="t in readonlyTables"
            :key="t"
            :model-value="selectedTables.includes(t)"
            disabled
          >{{ t }}</el-checkbox>
        </div>
        <div class="table-count-hint">
          已选 {{ selectedTables.length }}{{ savedTotalTables > 0 ? ` / ${savedTotalTables}` : '' }} 张表
        </div>
      </div>

      <div v-if="connectionTested && tables.length > 0 && form.type !== 'excel_csv'" class="table-section">
        <el-divider />
        <div class="section-label">选择要用于 Text2SQL 查询的表</div>
        <div class="table-checkbox-controls">
          <el-checkbox
            :model-value="checkAll"
            :indeterminate="isIndeterminate"
            @change="handleCheckAllChange"
          >
            全选
          </el-checkbox>
          <el-tag size="small" type="info" effect="plain">
            已选 {{ selectedTables.length }} / {{ tables.length }}
          </el-tag>
        </div>
        <el-checkbox-group v-model="selectedTables" class="table-checkbox-group">
          <el-checkbox v-for="table in tables" :key="table" :label="table">
            {{ table }}
          </el-checkbox>
        </el-checkbox-group>
        <div v-if="fetchingTables" class="table-loading">
          <el-icon class="is-loading"><Loading /></el-icon> 正在获取表列表...
        </div>
      </div>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button :loading="testing" :disabled="!canTest" @click="handleTest">测试连接</el-button>
      <el-button type="primary" :loading="saving" :disabled="!canSave" @click="handleSave">保存</el-button>
    </template>
  </el-drawer>
</template>

<style scoped>
.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.file-upload {
  width: 100%;
}

.file-upload :deep(.el-upload) {
  width: 100%;
}

.file-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 22px 16px;
}

.upload-icon {
  font-size: 32px;
  color: #409eff;
}

.upload-text {
  margin-top: 6px;
  color: #606266;
}

.upload-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  font-size: 13px;
  color: #606266;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
  width: 100%;
}

.file-row {
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafafa;
}

.file-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-meta {
  min-width: 0;
  flex: 1;
}

.file-name {
  color: #303133;
  font-size: 13px;
  word-break: break-all;
}

.file-sub {
  margin-top: 2px;
  color: #909399;
  font-size: 12px;
}

.sheet-select {
  width: 100%;
  margin-top: 8px;
}

.test-result {
  margin-top: 16px;
}

.table-section {
  margin-top: 4px;
}

.section-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.table-count-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.table-checkbox-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.table-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.table-checkbox-group .el-checkbox {
  width: 50%;
  margin-right: 0;
}

.table-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 0;
  color: #909399;
  font-size: 13px;
}
</style>
