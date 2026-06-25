<script setup lang="ts">
defineProps<{
  suggestions: string[]
  loading: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  select: [question: string]
}>()
</script>

<template>
  <div v-if="suggestions.length" class="quick-prompts" aria-label="快捷提问">
    <span class="prompts-label">快捷提问</span>
    <el-tag
      v-for="question in suggestions"
      :key="question"
      class="prompt-tag"
      size="small"
      :class="{ 'is-loading': loading }"
      :aria-disabled="disabled"
      @click="!disabled && emit('select', question)"
    >
      {{ question }}
    </el-tag>
  </div>
</template>

<style scoped>
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
  color: var(--ops-text-muted);
  white-space: nowrap;
  margin-right: 2px;
  flex-shrink: 0;
}

.prompt-tag {
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid var(--ops-border);
  color: var(--ops-text-secondary);
  background: #fff;
  white-space: nowrap;
}

.prompt-tag:hover {
  color: var(--ops-primary);
  border-color: rgba(47, 125, 246, 0.38);
  background: var(--ops-primary-soft);
}

.prompt-tag[aria-disabled='true'] {
  cursor: default;
  opacity: 0.55;
}

.prompt-tag.is-loading {
  opacity: 0.72;
}
</style>