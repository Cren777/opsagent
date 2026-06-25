<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import ChatMessageList from '@/components/chat/ChatMessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import QuickQuestions from '@/components/chat/QuickQuestions.vue'
import { useQuestionSuggestions } from '@/composables/useQuestionSuggestions'

const chatStore = useChatStore()
const configStore = useConfigStore()
const authStore = useAuthStore()

const showLLMWarning = computed(
  () => configStore.llmProvidersLoaded && configStore.llmProviders.length === 0
)

const draft = ref('')
const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null)
const userId = computed(() => authStore.user?.id || '')
const sessionId = computed(() => chatStore.activeSessionId || '')
const contextVersion = computed(() => String(chatStore.activeSession?.updatedAt || 0))
const datasourceId = computed({
  get: () => chatStore.selectedDatasourceId,
  set: (value: string | null) => { chatStore.selectedDatasourceId = value },
})

const { suggestions, isLoading: suggestionsLoading } = useQuestionSuggestions({
  draft,
  userId,
  sessionId,
  contextVersion,
  history: computed(() => chatStore.requestHistory),
  datasourceId,
  attachments: computed(() => chatStore.pendingAttachments),
  isStreaming: computed(() => chatStore.isStreaming),
})

function selectSuggestion(question: string) {
  draft.value = question
  requestAnimationFrame(() => chatInputRef.value?.focus())
}

watch(() => chatStore.activeSessionId, () => { draft.value = '' })

onMounted(() => {
  configStore.fetchDataSources()
  configStore.fetchLLMProviders()
})
</script>

<template>
  <div class="chat-view">
    <el-alert
      v-if="showLLMWarning"
      title="未配置 LLM 模型引擎"
      description="Text2SQL 功能需要至少一个 LLM 提供商。请前往「大模型配置」页面添加 OpenAI 兼容接口或 DashScope 提供商。"
      type="warning"
      show-icon
      closable
      class="llm-warning"
    />
    <ChatMessageList />
    <div class="chat-footer">
      <div class="footer-card">
        <div class="toolbar">
          <div v-if="configStore.dataSources.length > 0" class="ds-select">
            <el-icon><Coin /></el-icon>
            <el-select
              v-model="chatStore.selectedDatasourceId"
              placeholder="默认数据源"
              clearable
              size="small"
              class="ds-select-el"
            >
              <el-option
                v-for="ds in configStore.dataSources"
                :key="ds.id"
                :label="ds.name"
                :value="ds.id"
              >
                <span>{{ ds.name }}</span>
                <el-tag v-if="ds.is_active" size="small" type="success" effect="plain" style="margin-left: 6px">活跃</el-tag>
              </el-option>
            </el-select>
          </div>
          <div class="toolbar-divider" v-if="configStore.dataSources.length > 0 && suggestions.length" />
          <QuickQuestions
            :suggestions="suggestions"
            :loading="suggestionsLoading"
            :disabled="chatStore.isLoading"
            @select="selectSuggestion"
          />
        </div>
        <ChatInput ref="chatInputRef" v-model="draft" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background:
    radial-gradient(circle at 50% 0%, rgba(47, 125, 246, 0.12), transparent 36rem),
    linear-gradient(180deg, rgba(248, 250, 252, 0.85), rgba(232, 238, 246, 0.72)),
    var(--ops-bg);
}

.llm-warning {
  flex-shrink: 0;
  margin: 12px 18px 0;
  border-radius: var(--ops-radius);
}

.chat-footer {
  flex-shrink: 0;
  padding: 0 18px 18px;
}

.footer-card {
  max-width: 1280px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 12px;
  border: 1px solid var(--ops-border);
  box-shadow: var(--ops-shadow-md);
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--ops-surface-muted);
  border-bottom: 1px solid var(--ops-border-soft);
}

.ds-select {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  color: var(--ops-text-secondary);
  font-size: 13px;
}

.ds-select-el {
  width: 190px;
}

.toolbar-divider {
  width: 1px;
  height: 22px;
  background: var(--ops-border);
  flex-shrink: 0;
}


@media (max-width: 900px) {
  .toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-divider {
    display: none;
  }
}
</style>
