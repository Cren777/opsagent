<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useConfigStore } from '@/stores/config'
import DataSourceTypeCard from '@/components/datasource/DataSourceTypeCard.vue'
import DataSourceForm from '@/components/datasource/DataSourceForm.vue'

const configStore = useConfigStore()
const formRef = ref<InstanceType<typeof DataSourceForm> | null>(null)
const editingId = ref<string | undefined>()
const testingId = ref<string | null>(null)
const activeSource = computed(() => configStore.dataSources.find((source) => source.is_active))
const relationalCount = computed(() =>
  configStore.dataSources.filter((source) => source.type === 'mysql' || source.type === 'clickhouse').length
)
const fileSourceCount = computed(() =>
  configStore.dataSources.filter((source) => source.type === 'excel_csv').length
)

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

    <div class="config-overview">
      <div class="overview-card primary">
        <div class="overview-icon"><el-icon><Coin /></el-icon></div>
        <div>
          <div class="overview-label">数据源总数</div>
          <div class="overview-value">{{ configStore.dataSources.length }}</div>
        </div>
      </div>
      <div class="overview-card success">
        <div class="overview-icon"><el-icon><CircleCheck /></el-icon></div>
        <div>
          <div class="overview-label">当前活跃</div>
          <div class="overview-value text">{{ activeSource?.name || '未设置' }}</div>
        </div>
      </div>
      <div class="overview-card">
        <div class="overview-icon"><el-icon><DataAnalysis /></el-icon></div>
        <div>
          <div class="overview-label">关系型连接</div>
          <div class="overview-value">{{ relationalCount }}</div>
        </div>
      </div>
      <div class="overview-card">
        <div class="overview-icon"><el-icon><Document /></el-icon></div>
        <div>
          <div class="overview-label">文件数据源</div>
          <div class="overview-value">{{ fileSourceCount }}</div>
        </div>
      </div>
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
  padding: 28px 36px;
  width: 100%;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.page-header h2 {
  margin: 0 0 6px;
  font-size: 22px;
  color: var(--ops-text);
  font-weight: 800;
}

.page-desc {
  margin: 0;
  font-size: 14px;
  color: var(--ops-text-secondary);
}

.config-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 78px;
  padding: 15px 16px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--ops-border);
  border-radius: var(--ops-radius-lg);
  box-shadow: var(--ops-shadow-sm);
}

.overview-card.primary .overview-icon {
  color: var(--ops-primary);
  background: var(--ops-primary-soft);
}

.overview-card.success .overview-icon {
  color: var(--ops-success);
  background: rgba(24, 160, 88, 0.1);
}

.overview-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  color: var(--ops-text-secondary);
  background: var(--ops-surface-muted);
  font-size: 18px;
  flex: 0 0 auto;
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

.overview-value.text {
  max-width: 220px;
  font-size: 17px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.empty-wrap {
  display: flex;
  justify-content: center;
  padding: 70px 0;
  background: var(--ops-surface);
  border: 1px dashed var(--ops-border);
  border-radius: var(--ops-radius-lg);
}

@media (max-width: 900px) {
  .datasource-view {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
  }

  .config-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .source-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .config-overview {
    grid-template-columns: 1fr;
  }

  .source-grid {
    grid-template-columns: 1fr;
  }
}
</style>
