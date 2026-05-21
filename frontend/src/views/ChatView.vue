<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useConfigStore } from '@/stores/config'
import ChatMessageList from '@/components/chat/ChatMessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const chatStore = useChatStore()
const configStore = useConfigStore()

const hasLLM = computed(() => configStore.llmProviders.length > 0)

const demoQueries = [
  '如何查看磁盘使用率？',
  '最近一周有哪些critical告警？',
  'web-01服务器CPU使用率100%，帮我排查',
  '数据库连接数满了怎么处理？',
  '每个服务器上运行了多少个服务？',
  '系统日志中出现大量Permission denied错误',
  '过去7天工单平均处理时间是多少？',
  'nginx服务无法启动怎么排查？',
]

function sendDemo(query: string) {
  chatStore.sendStreamMessage(query)
}

onMounted(() => {
  configStore.fetchDataSources()
  configStore.fetchLLMProviders()
})
</script>

<template>
  <div class="chat-view">
    <el-alert
      v-if="!hasLLM"
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
          <div class="toolbar-divider" v-if="configStore.dataSources.length > 0" />
          <div class="quick-prompts">
            <span class="prompts-label">快捷提问</span>
            <el-tag
              v-for="demo in demoQueries"
              :key="demo"
              class="prompt-tag"
              size="small"
              @click="sendDemo(demo)"
            >
              {{ demo }}
            </el-tag>
          </div>
        </div>
        <ChatInput />
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.llm-warning {
  flex-shrink: 0;
  margin: 0;
  border-radius: 0;
}

.chat-footer {
  flex-shrink: 0;
  padding: 0 16px 16px;
}

.footer-card {
  max-width: 900px;
  margin: 0 auto;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #e8eaed;
  box-shadow: 0 -1px 12px rgba(0, 0, 0, 0.04), 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #f0f0f0;
}

.ds-select {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  color: #86909c;
  font-size: 13px;
}

.ds-select-el {
  width: 180px;
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: #e5e6eb;
  flex-shrink: 0;
}

.quick-prompts {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  overflow: hidden;
  flex-wrap: wrap;
}

.prompts-label {
  font-size: 12px;
  color: #c9cdd4;
  white-space: nowrap;
  margin-right: 2px;
  flex-shrink: 0;
}

.prompt-tag {
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid #e5e6eb;
  color: #86909c;
  background: #fff;
  white-space: nowrap;
}

.prompt-tag:hover {
  color: #409eff;
  border-color: #409eff;
  background: #ecf5ff;
}
</style>
