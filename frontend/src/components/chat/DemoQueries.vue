<script setup lang="ts">
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()

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
</script>

<template>
  <div class="demo-queries">
    <div class="demo-queries-inner" v-if="!chatStore.isLoading">
      <el-tag
        v-for="demo in demoQueries"
        :key="demo"
        class="demo-tag"
        size="small"
        :hit="false"
        @click="sendDemo(demo)"
      >
        {{ demo }}
      </el-tag>
    </div>
  </div>
</template>

<style scoped>
.demo-queries {
  padding: 0 20px 8px;
}

.demo-queries-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.demo-tag {
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid #d9ecff;
  color: #409eff;
  background: #ecf5ff;
}

.demo-tag:hover {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}
</style>
