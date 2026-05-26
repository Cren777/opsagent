<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { DiagnosticRunResult, DiagnosticScript } from '@/types/diagnostic'
import { fetchDiagnosticScripts, runDiagnosticScript } from '@/api/diagnostics'

const scripts = ref<DiagnosticScript[]>([])
const loading = ref(false)
const running = ref<string | null>(null)
const result = ref<DiagnosticRunResult | null>(null)
const resultVisible = ref(false)

onMounted(loadScripts)

async function loadScripts() {
  loading.value = true
  try {
    const { data } = await fetchDiagnosticScripts()
    scripts.value = data
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
</script>

<template>
  <div class="ops-page">
    <div class="page-header">
      <div>
        <h2>诊断工具</h2>
        <p class="page-desc">查看并执行白名单中的安全诊断脚本</p>
      </div>
      <el-button :icon="'Refresh'" @click="loadScripts">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="scripts" border>
      <el-table-column prop="name" label="脚本" min-width="220" />
      <el-table-column prop="description" label="说明" min-width="260" />
      <el-table-column prop="timeout" label="超时" width="100" />
      <el-table-column prop="size" label="大小" width="100" />
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
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

    <el-drawer v-model="resultVisible" title="诊断结果" size="640px">
      <el-tag :type="result?.exit_code === '0' ? 'success' : 'danger'">
        Exit {{ result?.exit_code }}
      </el-tag>
      <h4>标准输出</h4>
      <pre class="output">{{ result?.stdout || '无输出' }}</pre>
      <h4>错误输出</h4>
      <pre class="output">{{ result?.stderr || '无输出' }}</pre>
    </el-drawer>
  </div>
</template>

<style scoped>
.ops-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 6px;
  font-size: 20px;
  color: #1a1a2e;
}

.page-desc {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.output {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
