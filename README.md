# OpsAgent — 企业 IT 运维智能客服

基于大模型的智能 IT 运维助手，支持 **RAG 知识检索 + Text2SQL 数据分析 + 故障排查** 的闭环智能运维。

## 项目架构总览

```
用户 (浏览器)
      │
      ▼
┌──────────────────────────────────────────────────┐
│                  FastAPI 服务 (8080)               │
│  ┌─────────────┐  ┌────────────┐  ┌────────────┐  │
│  │  静态文件服务  │  │  API 路由  │  │  中间件     │  │
│  │  (Vue SPA)  │  │  /api/*   │  │  CORS/认证  │  │
│  └─────────────┘  └─────┬──────┘  └────────────┘  │
└─────────────────────────┼──────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────┐ ┌─────────────────┐
│  意图分类器       │ │ 编排器   │ │  结果融合        │
│  规则 + LLM 两级  │ │Orchestr.│ │  结构化诊断报告   │
└─────────────────┘ └───┬─────┘ └─────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
┌──────────────┐ ┌────────────┐ ┌──────────────┐
│  RAG 检索    │ │  Text2SQL  │ │  故障排查     │
│  Milvus+BGE  │ │  MySQL/CK  │ │  日志+脚本    │
└──────────────┘ └────────────┘ └──────────────┘
```

## 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| 前端框架 | Vue 3 + Vite + TypeScript | 组件化 SPA |
| UI 组件库 | Element Plus | 中文友好的企业级组件 |
| 状态管理 | Pinia | Vue 3 官方状态管理 |
| 路由 | Vue Router 4 | 三页面 SPA 路由 |
| 后端框架 | FastAPI + Uvicorn | Python 异步 Web 框架 |
| 大模型 | DeepSeek / DashScope (百炼) | 双引擎自动 fallback |
| Embedding | BAAI/bge-large-zh-v1.5 | 1024 维，GPU 加载 |
| 向量数据库 | Milvus Lite | 嵌入式文件模式 |
| 关系数据库 | MySQL / ClickHouse / Excel&CSV | 可配置数据源 |
| 配置持久化 | SQLite + Fernet 加密 | 用户配置安全存储 |

---

## 📂 项目文件结构

```
OpsAgent/
├── config/                          # 系统配置
│   ├── settings.py                  # 全局配置（数据库/模型/路径等）
│   └── prompts/                     # Prompt 模板目录
│
├── frontend/                        # Vue 3 前端项目
│   ├── package.json                 # 前端依赖
│   ├── vite.config.ts               # Vite 构建配置
│   ├── tsconfig*.json               # TypeScript 配置
│   ├── index.html                   # Vite 入口 HTML
│   └── src/
│       ├── main.ts                  # Vue 应用入口 (挂载 Element Plus/Router/Pinia)
│       ├── App.vue                  # 根组件 (搭载 AppLayout)
│       ├── style.css                # 全局样式
│       ├── router/
│       │   └── index.ts             # 路由配置（/ → ChatView, /datasources, /llm）
│       ├── stores/
│       │   ├── chat.ts              # 对话状态 (消息列表/SSE 流式/加载状态)
│       │   └── config.ts            # 配置状态 (数据源/LLM 提供商 CRUD)
│       ├── api/
│       │   ├── client.ts            # Axios HTTP 客户端 (拦截器/错误处理)
│       │   ├── chat.ts              # 对话 API (chat + chat/stream)
│       │   ├── datasource.ts        # 数据源 API (CRUD + 测试 + 激活)
│       │   └── llm.ts               # LLM 提供商 API (CRUD + 测试 + 设为主力)
│       ├── types/
│       │   ├── chat.ts              # ChatMessage/ChatRequest/ChatResponse 类型
│       │   ├── datasource.ts        # DataSource 类型定义
│       │   └── llm.ts               # LLMProvider 类型定义
│       ├── views/
│       │   ├── ChatView.vue         # 智能对话页面 (主页面)
│       │   ├── DataSourceView.vue   # 数据源配置页面
│       │   └── LLMConfigView.vue    # 大模型配置页面
│       └── components/
│           ├── layout/
│           │   ├── AppLayout.vue    # 整体布局 (侧边栏 + 顶部 + 内容区)
│           │   └── AppSidebar.vue   # 左侧导航 (菜单 + 演示查询)
│           ├── chat/
│           │   ├── ChatMessage.vue       # 单条消息气泡 (Markdown/代码高亮)
│           │   ├── ChatMessageList.vue   # 消息列表容器 (自动滚动)
│           │   └── ChatInput.vue         # 输入框 + 发送按钮
│           ├── datasource/
│           │   ├── DataSourceTypeCard.vue # 数据源卡片 (类型图标/状态/操作)
│           │   └── DataSourceForm.vue    # 数据源表单 (el-drawer 侧拉面板)
│           └── shared/
│               ├── StatusBadge.vue        # 状态指示灯组件
│               └── ConfirmDialog.vue      # 确认弹窗组件
│
├── ops_agent/                       # Python 后端
│   ├── api/                         # API 层
│   │   ├── main.py                  # FastAPI 应用入口 (路由注册/静态文件/CORS)
│   │   ├── middleware/
│   │   │   └── auth.py              # API Key 认证中间件
│   │   ├── routes/
│   │   │   ├── health.py            # GET /health 健康检查
│   │   │   ├── chat.py              # POST /api/chat 对话 (流式+非流式)
│   │   │   └── config.py            # 配置 API (数据源/LLM CRUD)
│   │   ├── models/
│   │   │   └── config_models.py     # SQLAlchemy ORM 模型 (datasource/llm 表)
│   │   ├── services/
│   │   │   ├── config_service.py    # 配置 CRUD + Fernet 加密 + 默认种子
│   │   │   └── llm_factory.py       # 动态 LLM 客户端工厂
│   │   └── static/                  # 前端构建输出
│   │       └── dist/                # npm run build 输出目录
│   │
│   ├── core/                        # 核心业务层
│   │   ├── orchestrator.py          # 编排器 (意图→路由→融合→输出)
│   │   ├── intent/
│   │   │   ├── types.py             # IntentType 枚举定义
│   │   │   └── classifier.py        # 意图分类器 (规则快速通道 + LLM 精准分类)
│   │   ├── scheduler/
│   │   │   └── task_router.py       # 任务路由 (意图→处理器映射)
│   │   └── fusion/
│   │       └── response_fusion.py   # 结果融合 (知识QA/数据QA/故障诊断模板)
│   │
│   ├── models/                      # 模型层
│   │   ├── llm/
│   │   │   └── client.py            # LLM 客户端 (DeepSeek引擎/百炼引擎/自动fallback)
│   │   ├── embedding/
│   │   │   └── embedder.py          # BGE 嵌入模型 (GPU加载/查询前缀)
│   │   ├── rag/
│   │   │   ├── knowledge_base.py    # 知识库管理入口
│   │   │   ├── retriever.py         # RAG 检索器 (Embedding→Milvus搜索)
│   │   │   └── log_parser.py        # 日志解析索引器
│   │   ├── text2sql/
│   │   │   ├── generator.py         # Text2SQL 生成 (Schema→LLM→SQL)
│   │   │   ├── schema_manager.py    # Schema 内省缓存
│   │   │   └── sql_validator.py     # SQL 安全校验 (禁止写入/强制LIMIT)
│   │   └── tools/
│   │       ├── base_datasource.py     # 数据源抽象基类
│   │       ├── datasource_factory.py  # 数据源工厂 (从配置创建)
│   │       ├── mysql_source.py        # MySQL 数据源实现
│   │       ├── clickhouse_source.py   # ClickHouse 数据源实现
│   │       ├── excel_source.py        # Excel/CSV 数据源实现 (pandas)
│   │       ├── db_connector.py        # 旧版 MySQL 连接器 (向后兼容)
│   │       └── script_executor.py     # 诊断脚本执行器 (沙箱/超时/截断)
│   │
│   ├── data/                        # 数据层
│   │   ├── vector_store.py           # Milvus Lite 向量存储封装
│   │   └── document_loader.py        # Markdown 文档加载+分块
│   │
│   └── utils/                       # 工具
│       ├── exceptions.py            # 异常层次结构
│       └── logging_config.py        # Loguru 日志配置
│
├── data/                            # 数据目录
│   ├── knowledge/                   # 运维知识文档 (Markdown)
│   ├── logs/                        # 示例系统日志
│   ├── db_schema/                   # MySQL 建表语句 + 种子数据
│   ├── vectors/                     # Milvus Lite 向量数据
│   └── app_config.db                # SQLite 配置数据库
│
├── scripts/                         # 运维/初始化脚本
│   ├── init_db.py                   # 初始化 MySQL 数据库 (建表+种子)
│   ├── build_index.py               # 构建 Milvus 知识库索引
│   ├── demo_scenarios.py            # 演示场景脚本
│   └── approved/                    # 预审批诊断脚本
│       ├── check_disk.sh
│       ├── check_cpu.sh
│       ├── check_memory.sh
│       └── check_service.sh
│
├── tests/                           # 测试
│   ├── conftest.py                  # Pytest 配置
│   ├── test_intent.py               # 意图分类测试 (15 cases)
│   └── test_text2sql.py             # SQL 安全校验测试 (12 cases)
│
└── .env                             # 环境变量 (API Keys/数据库连接)
```

---

## 🌐 API 接口文档

所有接口启动后可通过 `/docs` 访问 Swagger 文档。

### 系统

| 方法 | 路径 | 说明 | 请求 | 响应 |
|------|------|------|------|------|
| GET | `/health` | 健康检查 | — | `{status, database, milvus}` |
| GET | `/` | SPA 前端 | — | index.html (Vue 应用) |

### 对话 (POST /api/chat)

| 路径 | 说明 | 请求体 | 响应体 |
|------|------|--------|--------|
| `/api/chat` | 非流式对话 | `{query, history?}` | `{answer, intent, sources, sql}` |
| `/api/chat/stream` | SSE 流式对话 | `{query, history?}` | SSE 事件流 |

**SSE 事件类型：**
- `event: intent` — `{type: "knowledge_query"|"data_analysis"|"fault_troubleshooting"}`
- `event: token` — `{text: "..."}` (逐块文本)
- `event: done` — `{intent, sources, sql}` (最终元数据)
- `event: error` — `{message: "..."}`

### 数据源配置 (POST /api/config/datasources)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/datasources` | 列出所有已配置数据源 |
| POST | `/api/config/datasources` | 创建数据源 |
| PUT | `/api/config/datasources/{id}` | 更新数据源 |
| DELETE | `/api/config/datasources/{id}` | 删除数据源 |
| POST | `/api/config/datasources/{id}/test` | 测试已保存数据源连接 |
| POST | `/api/config/datasources/test` | 测试新配置的连接 |
| POST | `/api/config/datasources/{id}/activate` | 设为活跃数据源 |

**DataSource 类型：**
- `mysql` — 字段: host, port, user, password, database, charset
- `clickhouse` — 字段: host, port, user, password, database
- `excel_csv` — 字段: file_path, sheet_name

### 大模型配置 (POST /api/config/llm)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/llm` | 列出所有 LLM 提供商 |
| POST | `/api/config/llm` | 创建 LLM 提供商 |
| PUT | `/api/config/llm/{id}` | 更新 LLM 提供商 |
| DELETE | `/api/config/llm/{id}` | 删除 LLM 提供商 |
| POST | `/api/config/llm/{id}/test` | 测试已保存提供商对话 |
| POST | `/api/config/llm/test` | 测试新配置的提供商 |
| POST | `/api/config/llm/{id}/primary` | 设为主力模型 |

**Provider 配置项：** name, provider_type(openai_compatible/dashscope), api_key, base_url, model, temperature, max_tokens, is_primary

---

## 🚀 快速启动

### 1. 环境准备

```bash
conda activate opsagent
cd ~/OpsAgent
```

### 2. 配置 API Keys

编辑 `.env` 文件，至少配置一个 LLM 的 API Key：
```env
DEEPSEEK_API_KEY=sk-xxxxx
```

### 3. 安装前端依赖并构建

```bash
cd frontend && npm install && npm run build && cd ..
```

### 4. 初始化 MySQL 数据库 (可选)

```bash
python scripts/init_db.py
python scripts/build_index.py
```

### 5. 启动服务

```bash
uvicorn ops_agent.api.main:app --host 0.0.0.0 --port 8080
```

浏览器打开 `http://localhost:8080`。

### 6. 前端开发模式 (热更新)

```bash
cd frontend && npm run dev
# 浏览器打开 http://localhost:5173，自动代理 API 到 backend:8080
```

### 7. 运行测试

```bash
cd ~/OpsAgent && python -m pytest tests/ -v
```

---

## 🔄 核心流程

### 对话处理流水线

```
用户输入查询
    │
    ▼
┌─────────────────────┐
│  意图分类器           │  ← 规则快速通道 (>0.8 置信度) / LLM 精准分类
│  ┌─ knowledge_query  │
│  ├─ data_analysis    │
│  └─ fault_trouble... │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  任务路由             │
│  ┌─ 知识查询 → RAG   │
│  ├─ 数据分析 → Text2 │
│  └─ 故障排查 → 并行   │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  结果融合 (LLM)      │
│  生成结构化答案       │
└─────────┬───────────┘
          ▼
    SSE 流式输出
 (intent → token → done)
```

### 故障排查并行处理

```
故障排查触发
    │
    ├─── asyncio.gather ───
    │          │
    ▼          ▼          ▼
  RAG检索    日志搜索    脚本执行
  (知识库)   (Milvus)   (沙箱)
    │          │          │
    └──────────┼──────────┘
               ▼
          LLM 综合诊断
        (证据→根因→方案)
```

---

## 🔒 安全机制

- **SQL 注入防护**：SQL 校验器拒绝 DROP/DELETE/INSERT/UPDATE/ALTER/TRUNCATE/CREATE 等 13 种危险操作，强制 LIMIT ≤ 200
- **脚本沙箱**：仅允许执行 `scripts/approved/` 下预审批脚本，硬超时 30s，输出截断至 5000 字符
- **密钥加密**：API Key 和数据库密码使用 Fernet (AES-128) 加密存储于 SQLite
- **API 认证**：可选 API Key 中间件，调试模式自动跳过
