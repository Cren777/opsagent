<script setup lang="ts">
import { ref } from 'vue'
import type { LLMProviderItem, LLMProviderFormData, LLMTestResult } from '@/types/llm'
import { useConfigStore } from '@/stores/config'

const configStore = useConfigStore()
const formVisible = ref(false)
const editingId = ref<string | undefined>()
const testVisible = ref<string | null>(null)
const testMsg = ref('')
const testResult = ref<LLMTestResult | null>(null)
const testing = ref(false)
const saving = ref(false)

const defaultForm = (): LLMProviderFormData => ({
  name: '',
  provider_type: 'openai_compatible',
  api_key: '',
  base_url: '',
  model: '',
  temperature: 0.1,
  max_tokens: 4096,
  is_primary: false,
})

const form = ref<LLMProviderFormData>(defaultForm())

const providerTypeOptions = [
  { label: 'OpenAI 兼容', value: 'openai_compatible' },
  { label: 'DashScope (阿里百炼)', value: 'dashscope' },
]

const baseUrlPresets = [
  { label: 'DeepSeek', value: 'https://api.deepseek.com' },
  { label: 'OpenAI', value: 'https://api.openai.com/v1' },
  { label: '阿里百炼', value: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { label: '自定义', value: '' },
]

function openForm(provider?: LLMProviderItem) {
  if (provider) {
    editingId.value = provider.id
    form.value = {
      name: provider.name,
      provider_type: provider.provider_type,
      api_key: '',
      base_url: provider.base_url,
      model: provider.model,
      temperature: provider.temperature,
      max_tokens: provider.max_tokens,
      is_primary: provider.is_primary,
    }
  } else {
    editingId.value = undefined
    form.value = defaultForm()
  }
  formVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const data = { ...form.value }
    if (!data.api_key && editingId.value) {
      // Keep old API key if not changed
    }
    await configStore.saveLLMProvider(data, editingId.value)
    formVisible.value = false
    configStore.fetchLLMProviders()
  } finally {
    saving.value = false
  }
}

async function handleTest(id: string) {
  testing.value = true
  testResult.value = null
  try {
    const result = await configStore.testLLM(id, testMsg.value || '你好，请简要介绍一下你自己。')
    testResult.value = result
  } finally {
    testing.value = false
  }
}

async function handleDelete(id: string) {
  await configStore.removeLLMProvider(id)
}

async function handleSetPrimary(id: string) {
  await configStore.setPrimaryLLM(id)
}
</script>

<template>
  <div class="llm-view">
    <div class="page-header">
      <div>
        <h2>大模型配置</h2>
        <p class="page-desc">管理大语言模型提供商，支持多模型自动 fallback</p>
      </div>
      <el-button type="primary" :icon="'Plus'" @click="openForm()">添加提供商</el-button>
    </div>

    <div v-if="configStore.llmProviders.length === 0" class="empty-wrap">
      <el-empty description="尚未配置大模型提供商" :image-size="100">
        <el-button type="primary" @click="openForm()">添加第一个提供商</el-button>
      </el-empty>
    </div>

    <div v-else class="provider-grid">
      <el-card
        v-for="provider in configStore.llmProviders"
        :key="provider.id"
        class="provider-card"
        :class="{ primary: provider.is_primary }"
        shadow="hover"
      >
        <div class="provider-header">
          <div>
            <div class="provider-name">
              {{ provider.name }}
              <el-tag v-if="provider.is_primary" size="small" type="success">主力</el-tag>
            </div>
            <div class="provider-model">{{ provider.model }}</div>
          </div>
          <div class="provider-type-tag">
            <el-tag size="small">{{ provider.provider_type === 'dashscope' ? 'DashScope' : 'OpenAI兼容' }}</el-tag>
          </div>
        </div>

        <div class="provider-info">
          <div class="info-row">
            <span class="info-label">API 地址</span>
            <span class="info-value">{{ provider.base_url }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">温度</span>
            <span class="info-value">{{ provider.temperature }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">最大 Token</span>
            <span class="info-value">{{ provider.max_tokens }}</span>
          </div>
        </div>

        <!-- Test Chat Area -->
        <div v-if="testVisible === provider.id" class="test-chat-area">
          <el-input
            v-model="testMsg"
            placeholder="输入测试消息..."
            :rows="2"
            type="textarea"
          />
          <div class="test-actions">
            <el-button size="small" :loading="testing" @click="handleTest(provider.id)">发送测试</el-button>
            <el-button size="small" text @click="testVisible = null">收起</el-button>
          </div>
          <div v-if="testResult" class="test-response">
            <div class="test-latency">延迟: {{ testResult.latency_ms }}ms</div>
            <div class="test-content">{{ testResult.response }}</div>
          </div>
        </div>

        <div class="provider-actions">
          <el-button size="small" text :icon="'ChatDotSquare'" @click="testVisible = testVisible === provider.id ? null : provider.id">
            测试
          </el-button>
          <el-button size="small" text :icon="'Edit'" @click="openForm(provider)">编辑</el-button>
          <el-popconfirm title="确定删除此提供商？" @confirm="handleDelete(provider.id)">
            <template #reference>
              <el-button size="small" text type="danger" :icon="'Delete'">删除</el-button>
            </template>
          </el-popconfirm>
          <el-button
            v-if="!provider.is_primary"
            size="small"
            type="primary"
            plain
            @click="handleSetPrimary(provider.id)"
          >
            设为主力
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- Add/Edit Drawer -->
    <el-drawer
      v-model="formVisible"
      :title="editingId ? '编辑大模型提供商' : '添加大模型提供商'"
      size="520px"
      destroy-on-close
    >
      <el-form label-position="top" size="default">
        <el-form-item label="提供商名称" required>
          <el-input v-model="form.name" placeholder="例如：DeepSeek、Qwen-Plus" />
        </el-form-item>

        <el-form-item label="接口类型" required>
          <el-select v-model="form.provider_type" style="width: 100%">
            <el-option
              v-for="opt in providerTypeOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="API Key" required>
          <el-input v-model="form.api_key" type="password" show-password placeholder="请输入 API Key" />
          <div v-if="editingId" class="form-hint">留空则保持原有 API Key 不变</div>
        </el-form-item>

        <el-form-item label="Base URL" required>
          <el-input v-model="form.base_url" placeholder="https://api.deepseek.com" />
          <div class="preset-urls">
            <el-button
              v-for="preset in baseUrlPresets"
              :key="preset.label"
              size="small"
              text
              @click="form.base_url = preset.value"
            >
              {{ preset.label }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="模型名称" required>
          <el-input v-model="form.model" placeholder="deepseek-chat / qwen-plus / gpt-4" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Temperature">
              <el-slider
                v-model="form.temperature"
                :min="0"
                :max="2"
                :step="0.1"
                :marks="{ 0: '0', 0.5: '0.5', 1: '1', 1.5: '1.5', 2: '2' }"
                show-input
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Max Tokens">
              <el-input-number
                v-model="form.max_tokens"
                :min="256"
                :max="128000"
                :step="256"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-switch v-model="form.is_primary" active-text="设为主力模型" />
          <div class="form-hint">主力模型将优先使用，其他模型作为 fallback</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!form.name || !form.base_url || !form.model" @click="handleSave">
          保存
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.llm-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0 0 6px;
  font-size: 20px;
  color: #1a1a2e;
}

.page-desc {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.provider-card {
  border: 2px solid transparent;
}

.provider-card.primary {
  border-color: #67c23a;
}

.provider-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.provider-name {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.provider-model {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
}

.provider-info {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: 13px;
}

.info-label {
  color: #909399;
}

.info-value {
  font-family: monospace;
  color: #606266;
  word-break: break-all;
  text-align: right;
  max-width: 60%;
}

.provider-actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.test-chat-area {
  margin: 12px 0;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.test-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.test-response {
  margin-top: 10px;
  padding: 10px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.test-latency {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.test-content {
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.preset-urls {
  display: flex;
  gap: 4px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.empty-wrap {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
</style>
