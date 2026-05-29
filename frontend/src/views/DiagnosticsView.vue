<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { DiagnosticRunResult, DiagnosticScript } from '@/types/diagnostic'
import {
  deleteDiagnosticScript,
  enableDiagnosticScript,
  fetchDiagnosticScripts,
  fetchPendingDiagnosticScripts,
  previewDiagnosticScript,
  runDiagnosticScript,
  uploadDiagnosticScript,
} from '@/api/diagnostics'

const scripts = ref<DiagnosticScript[]>([])
const pendingScripts = ref<DiagnosticScript[]>([])
const loading = ref(false)
const running = ref<string | null>(null)
const result = ref<DiagnosticRunResult | null>(null)
const resultVisible = ref(false)
const activeTab = ref('approved')
const fileInputRef = ref<HTMLInputElement | null>(null)
const previewVisible = ref(false)
const preview = ref<DiagnosticScript | null>(null)

onMounted(loadScripts)

async function loadScripts() {
  loading.value = true
  try {
    const [approved, pending] = await Promise.all([
      fetchDiagnosticScripts(),
      fetchPendingDiagnosticScripts(),
    ])
    scripts.value = approved.data
    pendingScripts.value = pending.data
  } finally {
    loading.value = false
  }
}

async function runScript(row: DiagnosticScript) {
  running.value = row.name
  try {
    const { data } = await runDiagnosticScript(row.name)
    result.value = data
    resultVisible.value = true
    ElMessage.success('诊断脚本执行完成')
  } finally {
    running.value = null
  }
}

function pickScript() {
  fileInputRef.value?.click()
}

async function onScriptChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  for (const file of files) {
    await uploadDiagnosticScript(file)
  }
  ElMessage.success('脚本已上传到待启用列表')
  await loadScripts()
}

async function openPreview(row: DiagnosticScript, status: string) {
  const { data } = await previewDiagnosticScript(row.name, status)
  preview.value = data
  previewVisible.value = true
}

async function enableScript(row: DiagnosticScript) {
  await enableDiagnosticScript(row.name)
  ElMessage.success('脚本已启用')
  await loadScripts()
}

async function removePending(row: DiagnosticScript) {
  await deleteDiagnosticScript(row.name, 'pending')
  ElMessage.success('脚本已删除')
  await loadScripts()
}
</script>

<template>
  <div class="ops-page">
    <div class="page-header">
      <div>
        <h2>诊断工具</h2>
        <p class="page-desc">上传、审核并执行白名单中的安全诊断脚本</p>
      </div>
      <div class="header-actions">
        <input ref="fileInputRef" class="file-input" type="file" accept=".sh,.py" multiple @change="onScriptChange" />
        <el-button :icon="'Upload'" @click="pickScript">上传脚本</el-button>
        <el-button :icon="'Refresh'" @click="loadScripts">刷新</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="已启用脚本" name="approved">
        <el-table v-loading="loading" :data="scripts" border>
          <el-table-column prop="name" label="脚本" min-width="220" />
          <el-table-column prop="description" label="说明" min-width="260" />
          <el-table-column prop="timeout" label="超时" width="100" />
          <el-table-column prop="size" label="大小" width="100" />
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text @click="openPreview(row, 'approved')">预览</el-button>
              <el-button
                size="small"
                type="primary"
                plain
                :loading="running === row.name"
                @click="runScript(row)"
              >
                执行
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="待启用脚本" name="pending">
        <el-table v-loading="loading" :data="pendingScripts" border>
          <el-table-column prop="name" label="脚本" min-width="220" />
          <el-table-column prop="description" label="说明" min-width="260" />
          <el-table-column prop="size" label="大小" width="100" />
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text @click="openPreview(row, 'pending')">预览</el-button>
              <el-button size="small" type="primary" plain @click="enableScript(row)">启用</el-button>
              <el-popconfirm title="确定删除此脚本？" @confirm="removePending(row)">
                <template #reference>
                  <el-button size="small" text type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="resultVisible" title="诊断结果" size="640px">
      <el-tag :type="result?.exit_code === '0' ? 'success' : 'danger'">
        Exit {{ result?.exit_code }}
      </el-tag>
      <h4>标准输出</h4>
      <pre class="output">{{ result?.stdout || '无输出' }}</pre>
      <h4>错误输出</h4>
      <pre class="output">{{ result?.stderr || '无输出' }}</pre>
    </el-drawer>

    <el-dialog v-model="previewVisible" :title="preview?.name" width="720px">
      <el-alert
        title="脚本只有启用后才允许执行，请确认脚本来源可信。"
        type="warning"
        show-icon
        :closable="false"
        class="preview-alert"
      />
      <pre class="output">{{ preview?.content || '无内容' }}</pre>
    </el-dialog>
  </div>
</template>

<style scoped>
.file-input {
  display: none;
}

.preview-alert {
  margin-bottom: 12px;
}

.output {
  background: #101828;
  color: #e4e7ec;
  border: 1px solid #1d2939;
  padding: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.65;
}
</style>
