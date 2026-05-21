<script setup lang="ts">
import { ref, reactive, watch, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import type { DataSourceFormData, ConnectionTestResult } from '@/types/datasource'
import { useConfigStore } from '@/stores/config'
import { fetchNewTables } from '@/api/datasource'

const props = defineProps<{ sourceId?: string }>()
const emit = defineEmits<{ saved: [] }>()

const configStore = useConfigStore()
const visible = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<ConnectionTestResult | null>(null)
const tables = ref<string[]>([])
const selectedTables = ref<string[]>([])
const fetchingTables = ref(false)
const connectionTested = ref(false)
const savedTotalTables = ref(0)

const isIndeterminate = computed(() => {
  return selectedTables.value.length > 0 && selectedTables.value.length < tables.value.length
})

const checkAll = computed(() => {
  return tables.value.length > 0 && selectedTables.value.length === tables.value.length
})

function handleCheckAllChange(val: boolean) {
  selectedTables.value = val ? [...tables.value] : []
}

const form = reactive<DataSourceFormData>({
  name: '',
  type: 'mysql',
  config: { host: '', port: 3306, user: '', password: '', database: '', charset: 'utf8mb4' },
})

async function open(source?: DataSourceFormData & { id?: string }) {
  // 重置状态
  testResult.value = null
  tables.value = []
  selectedTables.value = []
  connectionTested.value = false
  savedTotalTables.value = 0

  // 先设置表单数据，再显示抽屉（避免首次渲染空表单）
  if (source) {
    form.name = source.name
    form.type = source.type
    form.config = JSON.parse(JSON.stringify(source.config))
    const config = source.config as unknown as Record<string, unknown>
    const saved = config.selected_tables as string[] | undefined
    if (saved && saved.length > 0) {
      selectedTables.value = [...saved]
    }
    savedTotalTables.value = (config.total_tables as number) || 0
  } else {
    form.name = ''
    form.type = 'mysql'
    resetConfig()
  }

  await nextTick()
  visible.value = true
}

function resetConfig() {
  if (form.type === 'mysql') {
    form.config = { host: '', port: 3306, user: '', password: '', database: '', charset: 'utf8mb4' }
  } else if (form.type === 'clickhouse') {
    form.config = { host: '', port: 8123, user: '', password: '', database: '' }
  } else {
    form.config = { file_path: '', sheet_name: '' }
  }
}

watch(() => form.type, resetConfig)

const canTest = computed(() => {
  if (form.type === 'excel_csv') return !!(form.config as { file_path: string }).file_path
  const c = form.config as { host: string; database: string }
  return !!c.host && !!c.database
})

async function handleSave() {
  saving.value = true
  try {
    const payload = JSON.parse(JSON.stringify(form))
    if (selectedTables.value.length > 0) {
      payload.config.selected_tables = selectedTables.value
    }
    if (tables.value.length > 0) {
      payload.config.total_tables = tables.value.length
    } else if (savedTotalTables.value > 0) {
      payload.config.total_tables = savedTotalTables.value
    }
    await configStore.saveDataSource(payload, props.sourceId)
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
      await fetchTableList(oldSelection)
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
    // 只恢复之前已选且在当前表列表中仍存在的表，不自动全选
    if (oldSelection.length > 0) {
      selectedTables.value = oldSelection.filter((t) => tables.value.includes(t))
    } else {
      selectedTables.value = []
    }
  } catch {
    // 获取表列表失败时不阻塞用户
  } finally {
    fetchingTables.value = false
  }
}

defineExpose({ open })
</script>

<template>
  <el-drawer
    v-model="visible"
    :title="sourceId ? '编辑数据源' : '添加数据源'"
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

      <!-- MySQL / ClickHouse shared fields -->
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

      <!-- Excel/CSV -->
      <template v-else>
        <el-form-item label="文件路径" required>
          <el-input
            v-model="(form.config as { file_path: string }).file_path"
            placeholder="例如：/data/report.xlsx"
          />
          <div class="form-hint">请输入服务器上 Excel/CSV 文件的绝对路径</div>
        </el-form-item>
        <el-form-item label="工作表名（可选）">
          <el-input
            v-model="(form.config as { sheet_name: string }).sheet_name"
            placeholder="Sheet1（留空使用第一个工作表）"
          />
        </el-form-item>
      </template>

      <!-- Test Result -->
      <div v-if="testResult" class="test-result">
        <el-alert
          :title="testResult.ok ? '连接成功' : '连接失败'"
          :description="testResult.message + (testResult.latency_ms ? ` (延迟: ${testResult.latency_ms}ms)` : '')"
          :type="testResult.ok ? 'success' : 'error'"
          show-icon
          closable
        />
      </div>

      <!-- 未测试但有已保存的表：只读标签展示 -->
      <div v-if="!connectionTested && selectedTables.length > 0 && form.type !== 'excel_csv'" class="table-section">
        <el-divider />
        <div class="section-label">已选择的表（测试连接后可修改）</div>
        <div class="table-readonly-tags">
          <el-tag
            v-for="t in selectedTables"
            :key="t"
            size="small"
            class="saved-table-tag"
          >{{ t }}</el-tag>
        </div>
        <div class="table-count-hint">
          已选 {{ selectedTables.length }}{{ savedTotalTables > 0 ? ` / ${savedTotalTables}` : '' }} 张表
        </div>
      </div>

      <!-- 已测试通过：可编辑复选框 -->
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
      <el-button type="primary" :loading="saving" :disabled="!form.name" @click="handleSave">保存</el-button>
    </template>
  </el-drawer>
</template>

<style scoped>
.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
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

.table-readonly-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.saved-table-tag {
  font-family: monospace;
  font-size: 12px;
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
