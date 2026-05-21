# 修复计划：数据源配置与 LLM 引擎相关问题

## 背景

用户配置了数据源后查询表时遇到 "Text2SQL 生成失败: 无可用 LLM 引擎" 错误。同时需要解决三个 UX 问题：(1) 数据源卡片上的测试按钮无反馈，(2) 连接数据库后支持选择要查询的表，(3) 对话框中支持选择数据源。

---

## 问题 1：数据源卡片测试按钮无提示

**根因**：`DataSourceView.vue:32-34` 中 `handleTest()` 调用 `configStore.testConnection(id)` 但丢弃了返回值 —— 用户看不到任何成功/失败消息。

**修改：**
1. **[DataSourceView.vue](frontend/src/views/DataSourceView.vue)** — 添加 `import { ElMessage }`，添加 `testingId` 响应式变量，重写 `handleTest()` 展示成功/失败消息，传递 `:testing` prop 给卡片
2. **[DataSourceTypeCard.vue](frontend/src/components/datasource/DataSourceTypeCard.vue)** — 添加 `testing` prop，绑定 `:loading` 到测试按钮

---

## 问题 2：连接数据库后支持选择表

**设计**：在数据源配置 JSON 中添加 `selected_tables: string[]` 字段。测试连接成功后获取表列表并以复选框展示。SchemaManager 在查询时只使用选中的表。

**后端修改：**
1. **[config.py:routes](ops_agent/api/routes/config.py)** — 新增两个端点：
   - `POST /api/config/datasources/tables` — 为未保存的连接列出表
   - `GET /api/config/datasources/{ds_id}/tables` — 为已保存的数据源列出表
   - 使用 `_list_tables()` 辅助函数，临时创建数据源实例并调用 `get_tables()`
2. **[schema_manager.py](ops_agent/models/text2sql/schema_manager.py)** — 在 `refresh()` 中，获取表列表后，如果 `db.config` 中有 `selected_tables` 则过滤

**前端修改：**
3. **[datasource.ts:types](frontend/src/types/datasource.ts)** — 为 MySQLConfig 和 ClickHouseConfig 添加 `selected_tables?: string[]`
4. **[datasource.ts:api](frontend/src/api/datasource.ts)** — 添加 `fetchTables(id)` 和 `fetchNewTables(data)` API 调用
5. **[DataSourceForm.vue](frontend/src/components/datasource/DataSourceForm.vue)** — 测试成功后调用 `fetchNewTables()`，展示复选框组供用户选择表；保存时包含 `selected_tables`；编辑时恢复已选状态

---

## 问题 3：对话框内支持选择数据源

**设计**：在聊天请求中添加可选的 `datasource_id` 字段。如果提供，按 ID 创建数据源实例；否则回退到活跃数据源。在 ChatView 添加下拉选择器。

**后端修改：**
1. **[datasource_factory.py](ops_agent/models/tools/datasource_factory.py)** — 添加 `get_datasource_by_id(ds_id)`，按 ID 读取配置并创建对应的数据源实例
2. **[chat.py:routes](ops_agent/api/routes/chat.py)** — 在 ChatRequest 中添加 `datasource_id: Optional[str] = None`，传递给 orchestrator
3. **[orchestrator.py](ops_agent/core/orchestrator.py)** — `process()`/`process_stream()` 接受 `datasource_id`；通过 `**kwargs` 传递给 `router.route()`；在 `_handle_data_analysis()` 中，如果提供 `datasource_id` 则使用指定数据源
4. **[task_router.py](ops_agent/core/scheduler/task_router.py)** — `route()` 接受 `**kwargs` 并传递给处理器：`await handler(query, entities, **kwargs)`

**前端修改：**
5. **[chat.ts:types](frontend/src/types/chat.ts)** — 在 `ChatRequest` 中添加 `datasource_id?: string`
6. **[chat.ts:store](frontend/src/stores/chat.ts)** — 添加 `selectedDatasourceId` 响应式变量，在 `sendStreamMessage()` 和 `sendMessage()` 请求中包含它
7. **[ChatView.vue](frontend/src/views/ChatView.vue)** — 挂载时获取数据源列表；在消息列表和输入框之间添加 `<el-select>` 下拉框，绑定 `chatStore.selectedDatasourceId`

---

## 问题 4：优雅处理"无可用 LLM 引擎"错误

**设计**：在每一层改进错误信息；在没有 LLM 配置时展示警告横幅。

**后端修改：**
1. **[client.py](ops_agent/models/llm/client.py)** — 改进"无可用 LLM 引擎"消息，包含可操作的指引（"请先在「大模型配置」页面添加 LLM 提供商"）
2. **[orchestrator.py](ops_agent/core/orchestrator.py)** — 用 try/except 包裹 `_handle_data_analysis()` 方法，LLM/SQL 错误返回友好消息而非崩溃；同时包裹 `process()` 顶层
3. **[chat.py:routes](ops_agent/api/routes/chat.py)** — 在 `chat()` 端点中捕获异常，返回包含错误消息的 `ChatResponse` 而非 500 错误

**前端修改：**
4. **[ChatView.vue](frontend/src/views/ChatView.vue)** — 当没有 LLM 提供商时添加警告横幅 `<el-alert>`，附带跳转到 LLM 配置页面的链接

---

## 验证方法

1. **问题 1**：点击卡片测试按钮 → 能看到成功/失败的 ElMessage 提示，测试期间按钮显示加载状态
2. **问题 2**：测试连接后 → 表列表以复选框出现 → 勾选/取消 → 保存 → 验证 Text2SQL 只使用选中的表生成 Schema 提示
3. **问题 3**：下拉框显示所有数据源 → 选择一个 → 查询针对该数据源执行 → 清空选择 → 回退到活跃数据源
4. **问题 4**：删除所有 LLM 提供商 → 警告横幅出现 → 聊天查询返回友好错误而非 500 → 重新添加 LLM → 横幅消失，查询正常
