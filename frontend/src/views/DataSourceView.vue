<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useConfigStore } from '@/stores/config'
import DataSourceTypeCard from '@/components/datasource/DataSourceTypeCard.vue'
import DataSourceForm from '@/components/datasource/DataSourceForm.vue'

const configStore = useConfigStore()
const formRef = ref<InstanceType<typeof DataSourceForm> | null>(null)
const editingId = ref<string | undefined>()
const testingId = ref<string | null>(null)

onMounted(() => {
  configStore.fetchDataSources()
})

function handleAdd() {
  editingId.value = undefined
  formRef.value?.open()
}

function handleEdit(id: string) {
  editingId.value = id
  const source = configStore.dataSources.find((d) => d.id === id)
  if (source) {
    formRef.value?.open(source)
  }
}

async function handleDelete(id: string) {
  await configStore.removeDataSource(id)
}

async function handleTest(id: string) {
  testingId.value = id
  try {
    const result = await configStore.testConnection(id)
    if (result.ok) {
      ElMessage.success(result.message || '连接成功')
    } else {
      ElMessage.error(result.message || '连接失败')
    }
  } catch (e: unknown) {
    ElMessage.error('连接测试失败')
  } finally {
    testingId.value = null
  }
}

async function handleActivate(id: string) {
  await configStore.activateSource(id)
}

function handleSaved() {
  configStore.fetchDataSources()
}
</script>

<template>
  <div class="datasource-view">
    <div class="page-header">
      <div>
        <h2>数据源配置</h2>
        <p class="page-desc">管理 Text2SQL 自然语言查询的数据源连接</p>
      </div>
      <el-button type="primary" :icon="'Plus'" @click="handleAdd">添加数据源</el-button>
    </div>

    <div v-if="configStore.dataSources.length === 0" class="empty-wrap">
      <el-empty description="尚未配置数据源" :image-size="100">
        <el-button type="primary" @click="handleAdd">添加第一个数据源</el-button>
      </el-empty>
    </div>

    <div v-else class="source-grid">
      <DataSourceTypeCard
        v-for="source in configStore.dataSources"
        :key="source.id"
        :source="source"
        :testing="testingId === source.id"
        @edit="handleEdit"
        @delete="handleDelete"
        @test="handleTest"
        @activate="handleActivate"
      />
    </div>

    <DataSourceForm ref="formRef" :source-id="editingId" @saved="handleSaved" />
  </div>
</template>

<style scoped>
.datasource-view {
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

.source-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.empty-wrap {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
</style>
