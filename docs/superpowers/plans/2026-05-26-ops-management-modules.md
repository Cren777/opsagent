# 运维管理模块实施计划

> **给执行 Agent 的说明：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐步执行本计划。任务步骤使用复选框（`- [ ]`）跟踪进度。

**目标：** 为 OpsAgent 增加知识库管理、日志与案例、诊断工具、索引管理四个运维管理模块。

**架构：** 每个模块先实现职责清晰的后端服务和 FastAPI 路由，再增加对应的 Vue 页面与左侧导航入口。第一版保持同步执行，并沿用项目现有的本地文件、SQLite 和 Milvus Lite 存储方式。

**技术栈：** FastAPI、SQLite、Milvus Lite 封装、Vue 3、Pinia、Element Plus。

---

### 任务 1：后端服务

- [ ] 为知识文件、故障案例/日志元数据、诊断脚本列表、索引状态补充纯服务层测试。
- [ ] 实现边界清晰、接口精简、无 FastAPI 依赖的服务层。
- [ ] 验证服务层测试通过。

### 任务 2：API 路由

- [ ] 增加 `/api/knowledge`、`/api/logs`、`/api/incidents`、`/api/diagnostics`、`/api/indexes` 路由。
- [ ] 在 `ops_agent/api/main.py` 中注册新增路由。
- [ ] 上传接口使用原始请求体，并通过 `filename` 查询参数传递文件名，避免引入 multipart 依赖。

### 任务 3：前端模块

- [ ] 增加前端 API 客户端和 TypeScript 类型定义。
- [ ] 增加四个 Vue 页面，覆盖列表、上传/操作、状态展示等基础控件。
- [ ] 注册前端路由和左侧导航菜单。
- [ ] 运行 `vue-tsc` 类型检查。

### 任务 4：验证

- [ ] 运行新增服务的聚焦 pytest 测试。
- [ ] 对新增后端文件运行 Python 语法检查。
- [ ] 运行前端类型检查。
