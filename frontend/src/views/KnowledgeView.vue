<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { KnowledgeFile, KnowledgeTreeNode } from '@/types/knowledge'
import {
  createKnowledgeFolder,
  deleteKnowledgeFolder,
  deleteKnowledgeFile,
  fetchKnowledgeFile,
  fetchKnowledgeFiles,
  fetchKnowledgeTree,
  rebuildKnowledgeIndex,
  renameKnowledgeFolder,
  uploadKnowledgeFile,
} from '@/api/knowledge'

const PINNED_FOLDERS_KEY = 'opsagent:pinned-knowledge-folders'
const files = ref<KnowledgeFile[]>([])
const tree = ref<KnowledgeTreeNode[]>([])
const loading = ref(false)
const uploading = ref(false)
const rebuilding = ref(false)
const previewVisible = ref(false)
const preview = ref<KnowledgeFile | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const currentFolder = ref('')
const folderVisible = ref(false)
const folderName = ref('')
const folderParent = ref('')
const pinnedFolders = ref<string[]>(loadPinnedFolders())

const treeData = computed(() => sortTree(tree.value))
const indexedCount = computed(() => files.value.filter((file) => file.indexed).length)
const folderCount = computed(() => countFolders(tree.value))
const totalSize = computed(() => files.value.reduce((sum, file) => sum + (file.size || 0), 0))

const currentFiles = computed(() => {
  if (!currentFolder.value) return files.value
  return files.value.filter((file) => {
    const parent = file.relative_path.split('/').slice(0, -1).join('/')
    return parent === currentFolder.value
  })
})

onMounted(loadFiles)

async function loadFiles() {
  loading.value = true
  try {
    const [fileRes, treeRes] = await Promise.all([fetchKnowledgeFiles(), fetchKnowledgeTree()])
    files.value = fileRes.data
    tree.value = treeRes.data
  } finally {
    loading.value = false
  }
}

function pickFiles() {
  fileInputRef.value?.click()
}

function openCreateFolder(parent = currentFolder.value) {
  folderParent.value = parent
  folderName.value = ''
  folderVisible.value = true
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const selected = Array.from(input.files || [])
  input.value = ''
  if (!selected.length) return
  uploading.value = true
  try {
    for (const file of selected) {
      await uploadKnowledgeFile(file, file.name, currentFolder.value)
    }
    ElMessage.success(currentFolder.value ? `已上传到 ${currentFolder.value}` : '知识文件已上传')
    await loadFiles()
  } finally {
    uploading.value = false
  }
}

async function createFolder() {
  if (!folderName.value.trim()) return
  const path = folderParent.value ? `${folderParent.value}/${folderName.value.trim()}` : folderName.value.trim()
  await createKnowledgeFolder(path)
  ElMessage.success('文件夹已创建')
  folderName.value = ''
  folderVisible.value = false
  await loadFiles()
}

function selectNode(data: KnowledgeTreeNode) {
  currentFolder.value = data.relative_path
}

async function handleFolderCommand(command: unknown, data: KnowledgeTreeNode) {
  const action = String(command)
  if (action === 'create') {
    openCreateFolder(data.relative_path)
    return
  }
  if (action === 'rename') {
    await renameFolder(data)
    return
  }
  if (action === 'pin') {
    togglePinnedFolder(data.relative_path)
    return
  }
  if (action === 'delete') {
    await removeFolder(data)
  }
}

async function renameFolder(data: KnowledgeTreeNode) {
  const oldPath = data.relative_path
  const wasPinned = isPinned(oldPath)
  const result = await ElMessageBox.prompt('请输入新的文件夹名称', '重命名文件夹', {
    inputValue: data.name,
    inputPattern: /.+/,
    inputErrorMessage: '请输入文件夹名称',
    confirmButtonText: '保存',
    cancelButtonText: '取消',
  }).catch(() => null)
  if (!result) return
  const newName = String(result.value || '').trim()
  if (!newName || newName === data.name) return
  const { data: renamed } = await renameKnowledgeFolder(data.relative_path, newName)
  if (currentFolder.value === oldPath) {
    currentFolder.value = renamed.relative_path
  } else if (currentFolder.value.startsWith(`${oldPath}/`)) {
    currentFolder.value = `${renamed.relative_path}${currentFolder.value.slice(oldPath.length)}`
  }
  pinnedFolders.value = pinnedFolders.value
    .filter((path) => path !== oldPath)
    .concat(wasPinned ? [renamed.relative_path] : [])
  persistPinnedFolders()
  ElMessage.success('文件夹已重命名')
  await loadFiles()
}

async function removeFolder(data: KnowledgeTreeNode) {
  const confirmed = await ElMessageBox.confirm(
    `删除“${data.name}”后，文件夹内的知识文档也会一并删除。确认继续？`,
    '删除文件夹',
    {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    },
  ).then(() => true).catch(() => false)
  if (!confirmed) return
  await deleteKnowledgeFolder(data.relative_path, true)
  if (currentFolder.value === data.relative_path || currentFolder.value.startsWith(`${data.relative_path}/`)) {
    currentFolder.value = ''
  }
  pinnedFolders.value = pinnedFolders.value.filter(
    (path) => path !== data.relative_path && !path.startsWith(`${data.relative_path}/`),
  )
  persistPinnedFolders()
  ElMessage.success('文件夹已删除')
  await loadFiles()
}

function togglePinnedFolder(path: string) {
  if (isPinned(path)) {
    pinnedFolders.value = pinnedFolders.value.filter((item) => item !== path)
    ElMessage.success('已取消置顶')
  } else {
    pinnedFolders.value = [path, ...pinnedFolders.value]
    ElMessage.success('文件夹已置顶')
  }
  persistPinnedFolders()
}

function isPinned(path: string) {
  return pinnedFolders.value.includes(path)
}

function loadPinnedFolders() {
  try {
    const value = window.localStorage.getItem(PINNED_FOLDERS_KEY)
    return value ? (JSON.parse(value) as string[]) : []
  } catch {
    return []
  }
}

function persistPinnedFolders() {
  window.localStorage.setItem(PINNED_FOLDERS_KEY, JSON.stringify(pinnedFolders.value))
}

function sortTree(nodes: KnowledgeTreeNode[]): KnowledgeTreeNode[] {
  return nodes
    .map((node) => ({ ...node, children: sortTree(node.children || []) }))
    .sort((left, right) => {
      const pinnedDiff = Number(isPinned(right.relative_path)) - Number(isPinned(left.relative_path))
      return pinnedDiff || left.name.localeCompare(right.name, 'zh-Hans-CN')
    })
}

function countFolders(nodes: KnowledgeTreeNode[]): number {
  return nodes.reduce((sum, node) => sum + 1 + countFolders(node.children || []), 0)
}

function formatSize(size: number): string {
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${size} B`
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

    <div class="knowledge-overview">
      <div class="overview-card">
        <div class="overview-icon primary">
          <el-icon><Document /></el-icon>
        </div>
        <div>
          <div class="overview-label">文档总数</div>
          <div class="overview-value">{{ files.length }}</div>
        </div>
      </div>
      <div class="overview-card">
        <div class="overview-icon success">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div>
          <div class="overview-label">已索引</div>
          <div class="overview-value">{{ indexedCount }}</div>
        </div>
      </div>
      <div class="overview-card">
        <div class="overview-icon warning">
          <el-icon><FolderOpened /></el-icon>
        </div>
        <div>
          <div class="overview-label">知识目录</div>
          <div class="overview-value">{{ folderCount }}</div>
        </div>
      </div>
      <div class="overview-card">
        <div class="overview-icon muted">
          <el-icon><Files /></el-icon>
        </div>
        <div>
          <div class="overview-label">存储大小</div>
          <div class="overview-value">{{ formatSize(totalSize) }}</div>
        </div>
      </div>
    </div>

    <div class="manager-layout">
      <aside class="tree-panel">
        <div class="panel-title">
          <span>全部知识库</span>
          <el-button
            title="新建文件夹"
            aria-label="新建文件夹"
            size="small"
            text
            circle
            :icon="'Plus'"
            @click="openCreateFolder('')"
          />
        </div>
        <el-tree
          :data="treeData"
          node-key="relative_path"
          default-expand-all
          :props="{ label: 'name', children: 'children' }"
          highlight-current
          @node-click="selectNode"
        >
          <template #default="{ data }">
            <div class="tree-node">
              <span class="tree-label">
                <span v-if="data.relative_path && isPinned(data.relative_path)" class="pin-dot" />
                {{ data.name }}
              </span>
              <el-dropdown
                v-if="data.relative_path"
                trigger="click"
                @command="(command: unknown) => handleFolderCommand(command, data)"
              >
                <el-button
                  class="node-menu"
                  title="文件夹操作"
                  aria-label="文件夹操作"
                  size="small"
                  text
                  circle
                  :icon="'MoreFilled'"
                  @click.stop
                />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="pin">
                      {{ isPinned(data.relative_path) ? '取消置顶' : '置顶文件夹' }}
                    </el-dropdown-item>
                    <el-dropdown-item command="create">创建子文件夹</el-dropdown-item>
                    <el-dropdown-item command="rename">重命名</el-dropdown-item>
                    <el-dropdown-item command="delete" divided class="danger-item">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-tree>
      </aside>
      <section class="table-panel">
        <div class="folder-bar">
          <span>当前目录：{{ currentFolder || '全部知识库' }}</span>
        </div>
        <el-table v-loading="loading" :data="currentFiles" border>
          <el-table-column prop="filename" label="文件名" min-width="260" />
          <el-table-column prop="size" label="大小" width="110" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="索引" width="100">
            <template #default="{ row }">
              <el-tag :type="row.indexed ? 'success' : 'info'" size="small">
                {{ row.indexed ? '已索引' : '待重建' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text :icon="'View'" @click="openPreview(row)">预览</el-button>
              <el-popconfirm title="确定删除此知识文件？" @confirm="removeFile(row)">
                <template #reference>
                  <el-button
                    title="删除文件"
                    aria-label="删除文件"
                    size="small"
                    text
                    circle
                    type="danger"
                    :icon="'Close'"
                  />
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && currentFiles.length === 0" description="当前目录暂无知识文件" />
      </section>
    </div>

    <el-drawer v-model="previewVisible" title="知识文档预览" size="560px">
      <h3>{{ preview?.relative_path }}</h3>
      <pre class="preview-content">{{ preview?.content }}</pre>
    </el-drawer>

    <el-dialog v-model="folderVisible" title="新建知识库文件夹" width="420px">
      <el-input v-model="folderName" placeholder="请输入文件夹名称" />
      <template #footer>
        <el-button @click="folderVisible = false">取消</el-button>
        <el-button type="primary" @click="createFolder">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.file-input {
  display: none;
}

.preview-content {
  white-space: pre-wrap;
  word-break: break-word;
  background: #101828;
  color: #e4e7ec;
  border: 1px solid #1d2939;
  padding: 14px;
  line-height: 1.65;
}

.knowledge-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 76px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--ops-border);
  border-radius: var(--ops-radius-lg);
  box-shadow: var(--ops-shadow-sm);
}

.overview-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  font-size: 18px;
  flex: 0 0 auto;
}

.overview-icon.primary {
  color: var(--ops-primary);
  background: var(--ops-primary-soft);
}

.overview-icon.success {
  color: var(--ops-success);
  background: rgba(24, 160, 88, 0.1);
}

.overview-icon.warning {
  color: var(--ops-warning);
  background: rgba(217, 130, 43, 0.12);
}

.overview-icon.muted {
  color: var(--ops-text-secondary);
  background: var(--ops-surface-muted);
}

.overview-label {
  font-size: 12px;
  color: var(--ops-text-muted);
  margin-bottom: 3px;
}

.overview-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--ops-text);
}

.manager-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 18px;
}

.tree-panel,
.table-panel {
  min-width: 0;
}

.tree-panel {
  padding: 14px;
  background:
    linear-gradient(180deg, rgba(47, 125, 246, 0.04), transparent 160px),
    #fff;
}

.table-panel {
  overflow: hidden;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 700;
  margin-bottom: 10px;
  color: var(--ops-text);
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  gap: 6px;
}

.tree-label {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pin-dot {
  width: 6px;
  height: 6px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--ops-primary);
  flex: 0 0 auto;
}

.node-menu {
  opacity: 0;
  flex: 0 0 auto;
}

.tree-node:hover .node-menu {
  opacity: 1;
}

.folder-bar {
  padding: 13px 16px;
  background: var(--ops-surface-muted);
  border-bottom: 1px solid var(--ops-border);
  color: var(--ops-text-secondary);
  font-weight: 600;
}

@media (max-width: 1000px) {
  .knowledge-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .manager-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .knowledge-overview {
    grid-template-columns: 1fr;
  }
}
</style>
