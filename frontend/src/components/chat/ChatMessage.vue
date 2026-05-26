<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/types/chat'
import { ElMessage } from 'element-plus'
import { Marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const marked = new Marked(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code: string, lang: string) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value
      }
      return hljs.highlightAuto(code).value
    },
  })
)

const props = defineProps<{ message: ChatMessage }>()

const intentLabel = computed(() => {
  const map: Record<string, string> = {
    knowledge_query: '知识查询',
    data_analysis: '数据分析',
    fault_troubleshooting: '故障排查',
  }
  return map[props.message.intent || ''] || ''
})

const intentTagType = computed(() => {
  const map: Record<string, string> = {
    knowledge_query: 'primary',
    data_analysis: 'success',
    fault_troubleshooting: 'warning',
  }
  return map[props.message.intent || ''] || 'info'
})

const renderedMarkdown = computed(() => {
  if (!props.message.content) return ''
  return marked.parse(props.message.content) as string
})

const hasDiagnostics = computed(() => {
  const diagnostics = props.message.diagnostics
  if (props.message.intent !== 'fault_troubleshooting' || !diagnostics) return false
  return Boolean(
    diagnostics.case_match ||
    diagnostics.evidence?.length ||
    diagnostics.symptoms?.length
  )
})

const diagnostics = computed(() => props.message.diagnostics)

async function copySQL() {
  const sql = props.message.sql
  if (!sql) return

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(sql)
    } else {
      fallbackCopy(sql)
    }
    ElMessage.success('SQL 已复制')
  } catch {
    try {
      fallbackCopy(sql)
      ElMessage.success('SQL 已复制')
    } catch {
      ElMessage.error('复制失败，请手动选择 SQL 后复制')
    }
  }
}

function fallbackCopy(text: string) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const ok = document.execCommand('copy')
  document.body.removeChild(textarea)
  if (!ok) throw new Error('copy command failed')
}
</script>

<template>
  <div class="chat-message" :class="message.role">
    <div v-if="message.role === 'assistant'" class="message-avatar">
      <el-avatar :size="36" icon="Monitor" />
    </div>

    <div class="message-body">
      <div class="message-header" v-if="message.role === 'assistant' && message.intent">
        <el-tag :type="intentTagType" size="small">{{ intentLabel }}</el-tag>
      </div>

      <div class="message-bubble" :class="message.role">
        <div v-if="message.content" class="markdown-body" v-html="renderedMarkdown" />
        <div v-else-if="message.role === 'assistant'" class="streaming-cursor">
          <span class="cursor-blink">▊</span>
        </div>
      </div>

      <div v-if="message.sql" class="message-sql">
        <el-collapse>
          <el-collapse-item title="SQL 查询">
            <div class="sql-block">
              <pre><code>{{ message.sql }}</code></pre>
              <el-button size="small" text :icon="'CopyDocument'" @click="copySQL">复制</el-button>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <div v-if="hasDiagnostics" class="message-diagnostics">
        <el-collapse>
          <el-collapse-item title="故障排查证据">
            <div v-if="diagnostics?.case_match" class="diagnostic-block">
              <strong>命中历史案例：</strong>
              {{ diagnostics.case_match.case_id }}
              （{{ Math.round(diagnostics.case_match.score * 100) }}%）
            </div>
            <div v-if="diagnostics?.evidence?.length" class="diagnostic-block">
              <strong>证据：</strong>
              <ul>
                <li v-for="item in diagnostics.evidence" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div v-if="diagnostics?.symptoms?.length" class="diagnostic-block">
              <strong>症状：</strong>
              <el-tag
                v-for="item in diagnostics.symptoms"
                :key="item"
                size="small"
                type="info"
                class="symptom-tag"
              >
                {{ item }}
              </el-tag>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <div v-if="message.sources && message.sources.length > 0" class="message-sources">
        <span class="sources-label">参考来源：</span>
        <el-tag
          v-for="(src, i) in message.sources"
          :key="i"
          size="small"
          type="info"
          class="source-tag"
        >
          {{ src.title }}
        </el-tag>
      </div>

      <div v-if="message.attachments?.length" class="message-sources">
        <span class="sources-label">附件：</span>
        <el-tag
          v-for="item in message.attachments"
          :key="item.id"
          size="small"
          type="warning"
          class="source-tag"
        >
          {{ item.filename }}
        </el-tag>
      </div>

      <div class="message-time">
        {{ new Date(message.timestamp).toLocaleTimeString('zh-CN') }}
      </div>
    </div>

    <div v-if="message.role === 'user'" class="message-avatar">
      <el-avatar :size="36" icon="User" />
    </div>
  </div>
</template>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.chat-message.assistant {
  flex-direction: row;
}

.message-body {
  flex: 1;
  min-width: 0;
}

.message-header {
  margin-bottom: 6px;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
}

.message-bubble.user {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.markdown-body :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 14px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body :deep(code) {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
}

.markdown-body :deep(p) {
  margin: 0 0 8px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.markdown-body :deep(h3) {
  font-size: 15px;
  margin: 12px 0 6px;
}

.markdown-body :deep(h4) {
  font-size: 14px;
  margin: 10px 0 4px;
}

.message-bubble.user .markdown-body :deep(code) {
  background: rgba(255, 255, 255, 0.2);
  padding: 1px 4px;
  border-radius: 3px;
}

.message-bubble.assistant .markdown-body :deep(code) {
  background: #f0f2f5;
  padding: 1px 4px;
  border-radius: 3px;
  color: #e74c3c;
}

.streaming-cursor {
  display: inline;
}

.cursor-blink {
  animation: blink 0.8s infinite;
  color: #409eff;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.message-sql {
  margin-top: 8px;
}

.message-diagnostics {
  margin-top: 8px;
}

.diagnostic-block {
  font-size: 13px;
  color: #4e5969;
  margin-bottom: 8px;
}

.diagnostic-block ul {
  margin: 6px 0 0;
  padding-left: 18px;
}

.symptom-tag {
  margin: 4px 4px 0 0;
}

.sql-block {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.sql-block pre {
  flex: 1;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 10px 14px;
  border-radius: 6px;
  margin: 0;
  overflow-x: auto;
  font-size: 13px;
}

.message-sources {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
}

.sources-label {
  color: #909399;
}

.source-tag {
  cursor: default;
}

.message-time {
  margin-top: 4px;
  font-size: 11px;
  color: #c0c4cc;
}
</style>
