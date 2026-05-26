<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { KnowledgeFile } from '@/types/knowledge'
import {
  deleteKnowledgeFile,
  fetchKnowledgeFile,
  fetchKnowledgeFiles,
  rebuildKnowledgeIndex,
  uploadKnowledgeFile,
} from '@/api/knowledge'

const files = ref<KnowledgeFile[]>([])
const loading = ref(false)
const uploading = ref(false)
const rebuilding = ref(false)
const previewVisible = ref(false)
const preview = ref<KnowledgeFile | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

onMounted(loadFiles)

async function loadFiles() {
  loading.value = true
  try {
    const { data } = await fetchKnowledgeFiles()
    files.value = data
  } finally {
    loading.value = false
  }
}

function pickFiles() {
  fileInputRef.value?.click()
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const selected = Array.from(input.files || [])
  input.value = ''
  if (!selected.length) return
  uploading.value = true
  try {
    for (const file of selected) {
      await uploadKnowledgeFile(file)
    }
    ElMessage.success('知识文件已上传')
    await loadFiles()
  } finally {
    uploading.value = false
  }
}

async function openPreview(file: KnowledgeFile) {
  const { data } = await fetchKnowledgeFile(file.file_id)
  preview.value = data
  previewVisible.value = true
}

async function removeFile(file: KnowledgeFile) {
  await deleteKnowledgeFile(file.file_id)
  ElMessage.success('已删除')
  await loadFiles()
}

async function rebuildIndex() {
  rebuilding.value = true
  try {
    await rebuildKnowledgeIndex()
    ElMessage.success('知识库索引重建完成')
    await loadFiles()
  } finally {
    rebuilding.value = false
  }
}
</script>

<template>
  <div class="ops-page">
    <div class="page-header">
      <div>
        <h2>知识库管理</h2>
        <p class="page-desc">上传和管理运维知识文档，供智能对话检索引用</p>
      </div>
      <div class="header-actions">
        <input
          ref="fileInputRef"
          class="file-input"
          type="file"
          accept=".md,.txt"
          multiple
          @change="onFileChange"
        />
        <el-button :icon="'Upload'" :loading="uploading" @click="pickFiles">上传文档</el-button>
        <el-button type="primary" :icon="'Refresh'" :loading="rebuilding" @click="rebuildIndex">
          重建索引
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="files" border>
      <el-table-column prop="relative_path" label="文件路径" min-width="260" />
      <el-table-column prop="size" label="大小" width="110" />
      <el-table-column prop="updated_at" label="更新时间" width="180" />
      <el-table-column label="索引" width="100">
        <template #default="{ row }">
          <el-tag :type="row.indexed ? 'success' : 'info'" size="small">
            {{ row.indexed ? '已索引' : '待重建' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click="openPreview(row)">预览</el-button>
          <el-popconfirm title="确定删除此知识文件？" @confirm="removeFile(row)">
            <template #reference>
              <el-button size="small" text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && files.length === 0" description="暂无知识文件" />

    <el-drawer v-model="previewVisible" title="知识文档预览" size="560px">
      <h3>{{ preview?.relative_path }}</h3>
      <pre class="preview-content">{{ preview?.content }}</pre>
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

.header-actions {
  display: flex;
  gap: 8px;
}

.file-input {
  display: none;
}

.preview-content {
  white-space: pre-wrap;
  word-break: break-word;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  line-height: 1.6;
}
</style>
