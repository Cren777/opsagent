# OpsAgent — 项目整体指南（AI Agent 使用）

## 项目简介

OpsAgent 是一个基于大语言模型的智能运维助手。它提供 RAG 知识检索、Text2SQL 自然语言数据分析、日志文件分析、自动故障排查与历史案例复用的闭环工作流。用户通过 Web 聊天界面用自然语言提问，也可以上传日志文件或管理知识文档，完成运维查询、数据库分析、系统诊断和故障复盘。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router 4 |
| 后端 | Python 3.11+ / FastAPI + Uvicorn |
| 大模型引擎 | DeepSeek API（OpenAI 兼容）+ 阿里云百炼（DashScope），自动回退 |
| 向量化 | BAAI/bge-large-zh-v1.5 通过 SentenceTransformers |
| 向量数据库 | Milvus Lite（嵌入式文件模式） |
| 关系数据库 | MySQL（pymysql）、ClickHouse（clickhouse-connect）、Excel/CSV（pandas） |
| 配置存储 | SQLite + SQLAlchemy ORM，Fernet AES-128 加密 |
| 测试 | pytest（后端） |

## 项目结构

```
OpsAgent/
  ops_agent/            # Python 后端包
    api/                # FastAPI 路由、服务、ORM 模型
      routes/           # chat/config/uploads/knowledge/incidents/diagnostics/indexes 等接口
    core/               # 编排器、意图分类、任务路由、结果融合
    models/             # LLM、RAG、Text2SQL、知识库、索引、上传日志、故障案例、诊断脚本
      knowledge/        # 文件型知识库管理服务
      indexing/         # 知识库/日志/案例索引管理服务
      uploads/          # 用户上传日志保存、脱敏、预览和附件上下文
      troubleshooting/  # 故障案例记忆与相似案例复用
      tools/            # 数据源、脚本执行、诊断脚本管理
    data/               # Milvus 向量存储封装、文档加载器
    utils/              # 异常、日志
  frontend/             # Vue 3 SPA
    src/
      api/              # Axios API 客户端层
      components/       # Vue 组件（chat/、layout/、datasource/、shared/）
      router/           # Vue Router 配置
      stores/           # Pinia 状态管理
      types/            # TypeScript 类型定义
      views/            # Chat/DataSource/LLMConfig/Knowledge/LogsCases/Diagnostics/IndexManagement
  config/               # Pydantic 设置
  data/                 # 运行时数据（SQLite、知识库、上传日志、案例、schema、向量）
    knowledge/          # 用户知识库文档，支持目录分类
    uploads/logs/       # 用户上传日志及元数据
    vectors/            # Milvus Lite 数据文件
    incident_cases.db   # 自动保存的故障排查案例
  scripts/              # 工具脚本（init_db、build_index、demo_scenarios、approved 诊断脚本）
  tests/                # pytest 测试
```

## 架构流程

1. 用户通过 Vue 聊天界面提交查询 → POST `/api/chat` 或 `/api/chat/stream`（SSE）
2. 如果用户上传日志，前端先调用上传接口保存日志，再把 `attachments` 随聊天请求传入后端
3. 意图分类：正则快速匹配 → LLM 精确分类
   - `knowledge_query` → RAG 流水线（Milvus 向量搜索 + LLM 融合）
   - `data_analysis` → Text2SQL（schema 探查 → LLM 生成 SQL → 安全校验 → 执行 → 总结）
   - `fault_troubleshooting` → RAG + 上传日志上下文 + Milvus 日志搜索 + 安全诊断脚本 + 历史案例匹配 → LLM 诊断
4. 结果融合：LLM 从多源证据生成结构化回答
5. 流式输出：SSE 事件（`intent` → `token` 块 → `done` 附带元数据）

## 功能模块

| 模块 | 前端页面 | 后端接口/服务 | 说明 |
|---|---|---|---|
| 智能对话 | `ChatView.vue` | `/api/chat`、`/api/chat/stream`、`Orchestrator` | 支持普通问答、Text2SQL、日志附件故障排查 |
| 知识库管理 | `KnowledgeView.vue` | `/api/knowledge/*`、`KnowledgeService` | 支持上传 `.md/.txt`、目录分类、创建/重命名/删除文件夹、预览、重建索引 |
| 日志与案例 | `LogsCasesView.vue` | `/api/uploads/*`、`/api/incidents/*` | 支持上传日志查看、脱敏预览、故障案例管理和分类 |
| 诊断工具 | `DiagnosticsView.vue` | `/api/diagnostics/*`、`DiagnosticService` | 支持查看白名单脚本、上传待启用脚本、预览、启用、执行和删除 |
| 索引管理 | `IndexManagementView.vue` | `/api/indexes/*`、`IndexService` | 查看 Milvus collection 状态，重建知识库/日志/案例索引 |
| 数据源配置 | `DataSourceView.vue` | `/api/config/*` | 管理 MySQL、ClickHouse、Excel/CSV 等数据源 |
| 大模型配置 | `LLMConfigView.vue` | `/api/config/*` | 管理 OpenAI 兼容接口和 DashScope 提供商 |

## 关键约定

- **前后端通信**：REST API（Axios ↔ FastAPI），流式聊天使用 SSE
- **构建输出**：`npm run build` 输出到 `ops_agent/api/static/dist/`，由 FastAPI 以 SPA 降级路由提供
- **开发代理**：Vite 开发服务器将 `/api` 代理到 `localhost:8080`
- **配置管理**：数据源和 LLM 提供商存储在 SQLite 中，密钥加密存储
- **聊天附件**：日志上传后必须把 `attachments` 传给聊天接口；`type == "log"` 的附件应强制进入 `fault_troubleshooting`
- **日志意图**：`.log`、`日志文件`、`分析日志` 等请求应优先按故障排查处理，避免被下划线文件名误判为数据分析表名
- **知识库文件**：只允许 `.md`、`.txt`；文件展示使用文件名，路径用于目录过滤和后端定位
- **索引状态**：知识库重建成功后会写入索引状态，文件修改时间晚于索引时间时显示待重建
- **脚本执行**：仅执行 `scripts/approved/` 中的脚本，30 秒超时，输出截断 5000 字符；用户上传脚本先进入待启用区，经启用后才可执行
- **故障案例**：故障排查答案会自动保存为案例，后续相似问题优先复用历史处理方案

## 开发工作流

1. 后端：`uvicorn ops_agent.api.main:app --reload --port 8080`
2. 前端：`cd frontend && npm run dev`
3. 测试：`pytest tests/`
4. 构建：`cd frontend && npm run build`，然后重启后端

常用局部验证：

- 后端纯服务测试：`pytest tests/test_management_services.py tests/test_log_upload_service.py tests/test_incident_case_memory.py -q`
- 意图和编排契约测试：`pytest tests/test_intent.py tests/test_orchestrator_contract.py -q`
- 前端类型检查：`cd frontend && npx vue-tsc -p tsconfig.app.json --noEmit`
- Python 语法检查：`python -m py_compile <changed-python-files>`

## 关键安全规则

- **Text2SQL**：阻止 DROP/DELETE/INSERT/UPDATE/ALTER/TRUNCATE/CREATE — 仅允许 SELECT
- **Text2SQL**：强制 LIMIT ≤ 200
- **脚本执行器**：仅执行 `scripts/approved/` 中的脚本，不执行任意命令；脚本上传必须校验文件名、扩展名和大小
- **日志预览**：预览上传日志时需要脱敏常见密钥、密码、token 等敏感字段
- **路径安全**：知识库、日志和脚本管理接口必须防止 `..` 路径穿越，所有解析后的路径必须限制在对应数据目录内
- **SQLite 配置数据库**：包含加密密钥，不要提交到 git
- **运行时数据**：`data/uploads/`、`data/vectors/`、`data/incident_cases.db`、`data/app_config.db` 属于本地运行产物，不应作为源码提交
