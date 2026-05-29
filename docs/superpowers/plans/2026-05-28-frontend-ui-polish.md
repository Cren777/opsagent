# OpsAgent 前端视觉升级实施计划

> **给执行 Agent 的要求：** 实施本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行。每个步骤使用 checkbox（`- [ ]`）追踪进度。

**目标：** 将 OpsAgent 当前前端升级为更高级、更符合智能运维场景的控制台界面，同时保持现有接口、状态管理、路由和数据交互行为不变。

**架构思路：** 保留现有 Vue 3 + Element Plus 结构，不重写业务逻辑。先在 `frontend/src/style.css` 建立统一视觉变量和 Element Plus 基础样式，再逐步优化应用布局、侧边栏、聊天页、管理页、数据源卡片和大模型卡片。

**技术栈：** Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router 4、Scoped CSS、全局 CSS 变量。

---

## 一、修改范围

### 需要修改的展示层文件

- `frontend/src/style.css`
  - 增加全局主题变量。
  - 统一按钮、表格、标签、弹窗、抽屉、滚动条等基础视觉。

- `frontend/src/components/layout/AppLayout.vue`
  - 优化顶部栏、页面标题、运行状态标签和主工作区背景。

- `frontend/src/components/layout/AppSidebar.vue`
  - 优化深色侧边栏、导航激活态、品牌区和折叠态。

- `frontend/src/components/chat/SessionList.vue`
  - 优化会话历史列表的层级、间距、激活态和删除按钮。

- `frontend/src/views/ChatView.vue`
  - 优化聊天页背景、快捷提问区、数据源选择区和底部输入容器。

- `frontend/src/components/chat/ChatMessageList.vue`
  - 优化消息列表留白和空状态。

- `frontend/src/components/chat/ChatMessage.vue`
  - 优化用户消息、AI 回复卡片、Markdown、SQL、诊断证据、来源、附件和时间显示。

- `frontend/src/components/chat/ChatInput.vue`
  - 优化输入框、附件按钮、聚焦态、发送按钮和停止生成按钮。

- `frontend/src/views/KnowledgeView.vue`
  - 优化知识库管理页面、目录面板、表格面板和预览抽屉。

- `frontend/src/views/LogsCasesView.vue`
  - 优化日志与案例页面、Tab、表格、标签和预览弹窗。

- `frontend/src/views/DiagnosticsView.vue`
  - 优化诊断工具页面、脚本表格、脚本预览和执行结果抽屉。

- `frontend/src/views/IndexManagementView.vue`
  - 优化索引管理页面、状态区域、操作按钮和索引表格。

- `frontend/src/views/DataSourceView.vue`
  - 优化数据源配置页面、卡片网格、空状态和页面头部。

- `frontend/src/components/datasource/DataSourceTypeCard.vue`
  - 将数据源卡片升级为更像“基础设施资产卡”的展示形式。

- `frontend/src/views/LLMConfigView.vue`
  - 优化大模型提供商卡片、测试区域、表单抽屉和参数展示。

### 明确不修改的内容

- 不修改 `frontend/src/api/**`。
- 不修改 `frontend/src/stores/**` 的业务逻辑。
- 不修改后端接口。
- 不修改路由路径、请求字段、响应字段、组件 props、事件名称。
- 不修改 SSE 流式输出逻辑。
- 不新增第三方 UI 或图标库。

---

## 二、实施原则

- 视觉方向采用“智能运维控制台”风格：深色侧边栏 + 浅色主工作区 + 专业表格 + 状态化标签。
- 避免营销页式大面积装饰，优先保证运维查询、日志分析、表格管理和配置操作的可读性。
- 保持当前功能入口和交互习惯，用户不需要重新学习使用方式。
- 修改以 CSS 和现有模板结构调整为主，不引入复杂抽象。
- 每个任务完成后运行 `npm run build`，确保前端构建通过。

---

## 三、任务拆解

### 任务 1：建立全局视觉系统

**文件：**

- 修改：`frontend/src/style.css`

**步骤：**

- [ ] 在 `:root` 中增加主题变量，包括背景色、面板色、边框色、文字色、主色、成功色、告警色、危险色、侧边栏色、圆角、阴影、等宽字体。

- [ ] 将 `html, body` 的默认背景从普通灰色升级为控制台背景色，并统一使用主题文字色。

- [ ] 增加 Element Plus 全局样式覆盖：
  - 按钮圆角和主按钮颜色。
  - 标签圆角和字重。
  - 表格表头背景、hover 色、边框色、圆角和阴影。
  - Tabs 字重。
  - Dialog 和 Drawer 圆角。
  - `pre` / `code` 使用统一等宽字体。

- [ ] 执行构建检查：

```bash
cd frontend
npm run build
```

**预期结果：** 构建成功，页面基础控件视觉整体更统一。

---

### 任务 2：优化应用外壳和侧边栏

**文件：**

- 修改：`frontend/src/components/layout/AppLayout.vue`
- 修改：`frontend/src/components/layout/AppSidebar.vue`
- 修改：`frontend/src/components/chat/SessionList.vue`

**步骤：**

- [ ] 补全 `AppLayout.vue` 中的页面标题映射：
  - `/`：智能对话
  - `/knowledge`：知识库管理
  - `/logs-cases`：日志与案例
  - `/diagnostics`：诊断工具
  - `/indexes`：索引管理
  - `/datasources`：数据源配置
  - `/llm`：大模型配置

- [ ] 优化顶部栏：
  - 高度保持紧凑。
  - 使用半透明白色和细边框。
  - 页面标题加粗。
  - 运行状态标签保留现有逻辑，只调整视觉。

- [ ] 优化侧边栏：
  - 使用更深、更专业的墨蓝色。
  - 当前导航项增加左侧高亮线。
  - hover 和 active 状态更明确。
  - 折叠态宽度保持稳定。

- [ ] 优化会话历史：
  - 提升标题和时间层级。
  - 当前会话使用更清楚的蓝色背景。
  - 删除按钮仅在 hover 时出现，减少干扰。

- [ ] 执行构建检查：

```bash
cd frontend
npm run build
```

**预期结果：** 整体框架更像专业运维控制台，导航层级清晰，路由标题正确。

---

### 任务 3：优化聊天工作区和输入区

**文件：**

- 修改：`frontend/src/views/ChatView.vue`
- 修改：`frontend/src/components/chat/ChatMessageList.vue`
- 修改：`frontend/src/components/chat/ChatInput.vue`

**步骤：**

- [ ] 优化聊天页背景：
  - 使用浅色工作台背景。
  - 保持对话区域干净，避免花哨装饰影响阅读。

- [ ] 优化底部输入容器：
  - 将当前输入区升级为更精致的悬浮指令台。
  - 圆角控制在 12px 左右。
  - 使用细边框和轻阴影。

- [ ] 优化快捷提问区：
  - 快捷标签更轻量。
  - hover 时使用主色软背景。
  - 窄屏下允许换行，不遮挡输入框。

- [ ] 优化数据源选择区：
  - 保留现有 `v-model` 和选项数据。
  - 仅调整宽度、颜色、边距和分割线。

- [ ] 优化输入框：
  - 聚焦时显示主色描边和柔和外发光。
  - 附件按钮、发送按钮、停止按钮保留原有逻辑。
  - 不修改上传文件类型限制。

- [ ] 执行构建检查：

```bash
cd frontend
npm run build
```

**预期结果：** 聊天页更像“运维分析指令台”，输入区清晰但不遮挡内容。

---

### 任务 4：优化聊天消息和诊断报告展示

**文件：**

- 修改：`frontend/src/components/chat/ChatMessage.vue`

**步骤：**

- [ ] 优化消息整体布局：
  - 最大宽度与底部输入区保持一致。
  - 用户消息靠右，AI 消息靠左。
  - 移动端避免用户消息过窄。

- [ ] 优化用户消息：
  - 使用主色渐变或主色背景。
  - 保留白色文字。
  - 增加轻微阴影。

- [ ] 优化 AI 回复：
  - 使用白色卡片、细边框和轻阴影。
  - Markdown 标题、列表、段落间距更稳定。
  - 行高适合长篇诊断报告阅读。

- [ ] 优化代码和 SQL：
  - 代码块使用深色背景。
  - 内联代码使用浅红或浅灰背景。
  - SQL 折叠区保留现有复制逻辑。

- [ ] 优化诊断证据、症状、来源和附件：
  - 保留现有 `diagnostics`、`sources`、`attachments` 渲染逻辑。
  - 只调整标签、间距和颜色。

- [ ] 执行构建检查：

```bash
cd frontend
npm run build
```

**预期结果：** AI 回复更像结构化故障诊断报告，长文本、SQL、证据块更容易阅读。

---

### 任务 5：统一管理类页面风格

**文件：**

- 修改：`frontend/src/style.css`
- 修改：`frontend/src/views/KnowledgeView.vue`
- 修改：`frontend/src/views/LogsCasesView.vue`
- 修改：`frontend/src/views/DiagnosticsView.vue`
- 修改：`frontend/src/views/IndexManagementView.vue`

**步骤：**

- [ ] 在 `style.css` 中增加通用管理页类：
  - `.ops-page`
  - `.page-header`
  - `.page-desc`
  - `.header-actions`
  - `.table-panel`
  - `.tree-panel`
  - `.status-box`

- [ ] 删除各管理页面中重复的页面头部样式，避免多个页面各写一套。

- [ ] 优化知识库页面：
  - 左侧目录面板增加统一边框、圆角和白色背景。
  - 右侧表格面板使用统一白色面板。
  - 当前目录条使用浅灰背景。
  - 文档预览使用更适合阅读的代码/文本块样式。

- [ ] 优化日志与案例页面：
  - Tab 样式跟随全局。
  - 表格使用统一样式。
  - 关键模式标签保持紧凑。
  - 预览弹窗内容使用深色等宽文本块，适合看日志。

- [ ] 优化诊断工具页面：
  - 脚本表格统一视觉。
  - 脚本预览保留安全提示。
  - 执行结果 stdout/stderr 使用深色输出块。

- [ ] 优化索引管理页面：
  - Milvus 路径和目录信息用统一状态面板展示。
  - 索引重建按钮区支持换行。
  - 表格操作保留 Popconfirm。

- [ ] 执行构建检查：

```bash
cd frontend
npm run build
```

**预期结果：** 知识库、日志案例、诊断工具、索引管理页面看起来属于同一套后台系统。

---

### 任务 6：优化数据源卡片和大模型卡片

**文件：**

- 修改：`frontend/src/views/DataSourceView.vue`
- 修改：`frontend/src/components/datasource/DataSourceTypeCard.vue`
- 修改：`frontend/src/views/LLMConfigView.vue`

**步骤：**

- [ ] 优化数据源配置页：
  - 页面最大宽度控制在 1240px 左右。
  - 卡片使用响应式网格。
  - 空状态使用虚线面板，视觉更完整。

- [ ] 优化数据源卡片：
  - 类型图标、名称、类型、状态更清晰。
  - 连接信息放入浅色信息块。
  - 表数量使用主色软标签。
  - 当前活跃数据源使用绿色边框和轻外发光。
  - 保留测试、编辑、删除、设为活跃逻辑。

- [ ] 优化大模型配置页：
  - 页面布局与数据源配置页保持一致。
  - Provider 卡片使用统一资产卡风格。
  - 主力模型使用绿色边框和轻外发光。
  - Base URL、温度、Token 等参数仍使用现有字段展示。

- [ ] 优化大模型测试区：
  - 测试输入框和响应区域放入浅色子面板。
  - 延迟和响应内容层级更清楚。
  - 保留现有测试按钮逻辑。

- [ ] 执行构建检查：

```bash
cd frontend
npm run build
```

**预期结果：** 数据源和大模型配置页更像基础设施资产管理页面，状态更醒目，信息更易扫读。

---

### 任务 7：响应式检查和最终视觉 QA

**文件：**

- 只在发现具体视觉问题时，修改前面任务涉及的展示层文件。

**步骤：**

- [ ] 启动前端开发服务器：

```bash
cd frontend
npm run dev
```

**预期结果：** Vite 启动成功，默认端口为 `8086`。

- [ ] 检查桌面端页面：

```text
/
/knowledge
/logs-cases
/diagnostics
/indexes
/datasources
/llm
```

桌面端检查项：

```text
侧边栏当前导航清晰可见。
顶部标题与当前路由一致。
聊天输入区不遮挡消息。
AI 回复长文本可读。
SQL、日志、脚本输出不会撑破布局。
表格操作按钮没有被裁切。
数据源和大模型卡片排列整齐。
状态标签颜色明确但不刺眼。
```

- [ ] 检查窄屏页面，宽度约 `390px`：

```text
侧边栏折叠后仍可使用。
页面头部可以上下堆叠。
聊天输入框仍可输入和发送。
快捷提问不会遮挡输入区。
知识库目录和表格改为单列。
数据源和大模型卡片改为单列。
表格可以横向滚动，不强行挤压文字。
```

- [ ] 如果发现具体视觉问题，只做局部修复：
  - 快捷提问过高：限制最大高度并允许内部滚动。
  - 卡片按钮换行难看：增加 `row-gap`。
  - 长路径撑破卡片：增加 `word-break: break-all`。
  - 表格内容过密：调整行高或列宽。

- [ ] 运行最终构建：

```bash
cd frontend
npm run build
```

- [ ] 检查变更范围：

```bash
git diff -- frontend/src
```

**预期结果：**

```text
只出现 Vue 展示结构、Scoped CSS 和全局 CSS 的变化。
不出现 frontend/src/api 变化。
不出现后端文件变化。
不出现 Pinia store 业务逻辑变化。
```

---

## 四、验收标准

- 前端构建通过：`cd frontend && npm run build` 成功。
- 所有现有页面仍可访问。
- 聊天发送、停止生成、上传附件、快捷提问、数据源选择仍可使用。
- 知识库上传、预览、删除、重建索引入口仍存在。
- 日志与案例预览、分类、删除、状态更新入口仍存在。
- 诊断脚本上传、预览、启用、执行入口仍存在。
- 索引重建和清空入口仍存在。
- 数据源测试、编辑、删除、设为活跃入口仍存在。
- 大模型测试、编辑、删除、设为主力入口仍存在。
- 页面整体视觉从“默认后台组件”升级为“智能运维控制台”。

---

## 五、风险与控制

- **风险：样式覆盖影响 Element Plus 默认布局。**
  - 控制方式：全局覆盖只做低风险基础样式，复杂页面使用 scoped CSS。

- **风险：窄屏下聊天输入区或快捷提问遮挡内容。**
  - 控制方式：增加响应式规则，允许快捷标签换行或滚动。

- **风险：长日志、SQL、URL、路径撑破卡片或表格。**
  - 控制方式：代码块横向滚动，卡片信息使用 `word-break`，表格保持 Element Plus 横向滚动能力。

- **风险：误改业务逻辑。**
  - 控制方式：最终用 `git diff -- frontend/src` 检查，确保没有 API、store、后端变更。

---

## 六、建议执行顺序

1. 全局视觉系统。
2. 应用外壳和侧边栏。
3. 聊天工作区和输入区。
4. 聊天消息和诊断报告。
5. 管理类页面统一。
6. 数据源和大模型卡片。
7. 响应式检查和最终 QA。

这个顺序可以保证先建立统一视觉基础，再逐步处理高频页面，最后做全站检查。
