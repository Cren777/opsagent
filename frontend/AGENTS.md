# OpsAgent 前端 — 指南（AI Agent 使用）

## 技术栈

Vue 3（Composition API + `<script setup>`）+ TypeScript + Vite + Element Plus + Pinia + Vue Router 4 + Axios

## 项目结构

```
frontend/src/
  main.ts                 # 应用入口：初始化 Pinia、Element Plus（zh-CN）、Router、图标注册
  App.vue                 # 根组件 → <AppLayout>
  style.css               # 全局样式
  env.d.ts                # TypeScript 环境声明

  router/
    index.ts              # 路由：/ → ChatView，/datasources → DataSourceView，/llm → LLMConfigView

  stores/
    chat.ts               # 聊天状态：会话、消息、流式传输、localStorage 持久化
    config.ts             # 配置状态：数据源和 LLM 提供商的 CRUD

  api/
    client.ts             # Axios 实例，错误拦截器（ElMessage.error）
    chat.ts               # 聊天 API：POST /api/chat，SSE 流式传输通过 fetch + ReadableStream
    datasource.ts         # 数据源 CRUD：获取、创建、更新、删除、测试、激活、列出表
    llm.ts                # LLM 提供商 CRUD：获取、创建、更新、删除、测试、设置为主

  types/
    chat.ts               # ChatRequest、ChatResponse、ChatMessage、ChatSession
    datasource.ts         # DataSourceType 联合类型、配置接口、DataSourceItem、ConnectionTestResult
    llm.ts                # LLMProviderItem、LLMProviderFormData、LLMTestResult

  views/
    ChatView.vue          # 聊天页面：消息列表、示例查询、数据源选择器、输入框
    DataSourceView.vue    # 数据源管理：添加/编辑/删除/测试/激活
    LLMConfigView.vue     # LLM 提供商管理：添加/编辑/删除/测试/设为主

  components/
    layout/
      AppLayout.vue       # 主布局外壳：侧边栏 + 头部 + <router-view>
      AppSidebar.vue      # 导航侧边栏：导航链接、Logo、会话列表
    chat/
      ChatMessage.vue     # 消息气泡：Markdown 渲染（marked + highlight.js）、意图标签、SQL 复制、来源引用
      ChatMessageList.vue # 可滚动消息列表，新消息自动滚动
      ChatInput.vue       # 文本输入框：Enter 发送、Shift+Enter 换行、流式传输停止按钮
      DemoQueries.vue     # 快速示例查询标签
      SessionList.vue     # 多会话侧边栏：创建、删除、切换
    datasource/
      DataSourceTypeCard.vue  # 数据源卡片：图标、状态、操作按钮
      DataSourceForm.vue      # 滑出抽屉表单：数据源配置（按类型显示不同字段）
    shared/
      StatusBadge.vue     # 状态指示器（active/inactive/error）
      ConfirmDialog.vue   # 确认对话框组件
```

## 组件约定

- 所有新组件使用 **Composition API + `<script setup>`** + TypeScript
- Props 使用 `defineProps<{ ... }>()`，emit 使用 `defineEmits<{ ... }>()`
- 组件文件名使用 **PascalCase**（例如 `ChatMessage.vue`）
- 组件目录按领域分组（chat/、datasource/、layout/、shared/）
- 可复用的公共组件放在 `components/shared/`

## 状态管理（Pinia）

- **chat store**（`stores/chat.ts`）：管理会话数组、当前会话、每个会话的消息列表、流式状态。持久化到 localStorage
- **config store**（`stores/config.ts`）：管理数据源列表、LLM 提供商列表、表单模式（创建/编辑）、抽屉显示状态

## API 层

- 基础 Axios 实例在 `api/client.ts` — 自动添加 `/api` 前缀，错误拦截器显示 `ElMessage.error`
- 聊天流式传输使用原生 `fetch` + `ReadableStream` SSE 解析器（不用 Axios），解析 `intent`/`token`/`done`/`error` 事件
- API 文件按领域组织：`chat.ts`、`datasource.ts`、`llm.ts`

## 样式约定

- 使用 Element Plus 组件，`zh-CN` 语言包
- 全局样式在 `style.css`
- 组件内使用 `<style scoped>`，优先使用 Element Plus 主题变量
- CSS 变量统一间距和颜色

## 开发命令

```bash
npm run dev          # 启动 Vite 开发服务器（端口 5173，/api 代理到 :8080）
npm run build        # 构建到 ops_agent/api/static/dist/
npm run preview      # 预览生产构建
```

## 关键模式

- **SSE 流式传输**：`api/chat.ts` → `parseSSEStream()` 生成器函数，逐个解析 SSE 事件
- **localStorage 持久化**：聊天会话持久化，当前会话 ID 存储
- **抽屉表单**：`DataSourceForm.vue` 使用 Element Plus `<el-drawer>`，由 config store 控制
- **类型安全**：所有 API 响应都有类型定义，表单数据接口继承配置类型
- **路由结构**：Views 是页面级组件，Components 是可复用的构建块

## 常见注意事项

- 不要在 store 中直接从 `vue-router` 导入 — 使用 store 自身的状态
- 流式状态（`isStreaming`）必须仔细管理，防止重复请求
- localStorage 有 ~5MB 限制 — chat store 中处理了聊天历史截断
- 构建输出路径是 `../ops_agent/api/static/dist/`（相对于 frontend/）— 不要更改
