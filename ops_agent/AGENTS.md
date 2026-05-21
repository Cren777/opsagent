# OpsAgent 后端 — 指南（AI Agent 使用）

## 技术栈

Python 3.11+ / FastAPI + Uvicorn + SQLAlchemy + Loguru + Fernet（加密）+ pytest

## 项目结构

```
ops_agent/
  api/
    main.py                       # FastAPI 应用：CORS、生命周期、路由注册、SPA 静态文件挂载
    middleware/auth.py            # 可选 API-Key 认证中间件
    routes/
      __init__.py
      health.py                   # GET /health（数据库 + Milvus 健康检查）
      chat.py                     # POST /api/chat、POST /api/chat/stream（SSE）
      config.py                   # 完整 CRUD：数据源和 LLM 提供商
    models/
      config_models.py            # SQLAlchemy ORM：DataSourceConfigModel、LLMProviderConfigModel
    services/
      config_service.py           # 配置 CRUD，使用 Fernet AES-128 加密敏感信息
      llm_factory.py              # 从配置数据库动态创建 LLM 客户端
    static/
      dist/                       # 构建好的 Vue SPA（gitignored，由前端构建）

  core/
    orchestrator.py               # 核心编排器：分类 → 路由 → 融合 → 流式输出
    intent/
      types.py                    # IntentType 枚举、IntentResult 数据类
      classifier.py               # 两阶段分类：正则快速匹配 + LLM 精确分类
    scheduler/
      task_router.py              # IntentType → 处理函数映射
    fusion/
      response_fusion.py          # 按意图类型进行 LLM 驱动的结果融合

  models/
    llm/
      client.py                   # UnifiedLLMClient：DeepSeekEngine + BailianEngine，自动回退
    embedding/
      embedder.py                 # BGE-large-zh-v1.5，GPU 加载，SentenceTransformer
    rag/
      knowledge_base.py           # 文档加载 → 向量化 → Milvus 存储 → 检索
      retriever.py                # 查询向量化 + Milvus 搜索 → 上下文
      log_parser.py               # 系统日志解析器 → LogEntry → 时间窗口分块 → Milvus
    text2sql/
      generator.py                # LLM 提示词 + schema + 样例，SQL 提取
      schema_manager.py           # 数据库内省：表、列、样例行、JOIN 提示、缓存
      sql_validator.py            # 安全校验：阻止 DROP/DELETE/INSERT/UPDATE/ALTER/TRUNCATE/CREATE，强制 LIMIT ≤ 200
    tools/
      base_datasource.py          # 抽象基类：execute_query、health_check、get_tables、get_columns、get_sample_rows
      datasource_factory.py       # 读取活跃配置 → 返回 MySQL/ClickHouse/ExcelCSV 数据源
      mysql_source.py             # pymysql 实现
      clickhouse_source.py        # clickhouse-connect 实现
      excel_source.py             # pandas 实现的 Excel/CSV
      script_executor.py          # 沙箱：仅执行 approved/ 中的脚本，30 秒超时，5000 字符截断

  data/
    vector_store.py               # Milvus Lite 封装：集合管理、插入、搜索、清空
    document_loader.py            # Markdown 加载器 + 分块器（按标题、按 token 数量+重叠）

  utils/
    exceptions.py                 # 异常层级：OpsAgentError → LLMError/...、DatabaseError/...、SQLError/...、VectorStoreError/...、ScriptExecutionError
    logging_config.py             # Loguru 配置
```

## 架构流程

```
用户查询 → 编排器 → 意图分类器（正则 → LLM）
  ├─ knowledge_query      → RAG 流水线（向量化 → Milvus 搜索 → LLM 融合）
  ├─ data_analysis        → Text2SQL（schema 探查 → LLM 生成 SQL → 校验 → 执行 → LLM 总结）
  └─ fault_troubleshooting → 并行执行：RAG + 日志搜索 + 脚本执行 → LLM 诊断
                              → 结果融合 → SSE 流式推送客户端
```

## 核心模块与职责

### API 层（`api/`）
- `main.py`：应用入口。注册所有路由，挂载 SPA 静态文件，配置 CORS。使用 `lifespan` 管理启动和关闭。
- `routes/chat.py`：聊天端点。非流式 POST 和 SSE 流式。SSE 事件：`intent`、`token`、`done`、`error`。
- `routes/config.py`：数据源和 LLM 提供商的完整 CRUD。每个都有测试和激活/设为主子路由。
- `services/config_service.py`：业务逻辑层。敏感信息用 Fernet 加密存储，读取时解密。
- `services/llm_factory.py`：根据存储的提供商配置动态创建 LLM 客户端（支持 OpenAI 兼容和 DashScope）。

### 核心层（`core/`）
- `orchestrator.py`：中央协调器。接收查询，运行意图分类，路由到处理函数，融合结果。支持同步和流式两种路径。
- `intent/classifier.py`：两阶段分类。第一阶段：正则匹配关键词（置信度 ≥ 0.8 直接返回）。第二阶段：模糊查询调用 LLM 精确分类。
- `scheduler/task_router.py`：纯映射 — `IntentType` → 处理函数引用。
- `fusion/response_fusion.py`：接收处理函数输出 + 原始查询，生成最终 LLM 响应。不同意图类型使用不同的提示词模板。

### 模型层（`models/`）
- `llm/client.py`：两个引擎实现共享同一接口。自动回退：主引擎失败则尝试备用引擎。
- `rag/`：完整 RAG 流水线 — 知识库管理、日志解析与索引、向量检索。
- `text2sql/`：带 schema 感知的 SQL 生成。**安全关键**：`sql_validator.py` 必须在执行前调用。
- `tools/`：数据源抽象层。工厂模式根据活跃配置创建正确的实现。`script_executor.py` 是沙箱模式 — 仅执行 `scripts/approved/` 中的脚本。

### 数据层（`data/`）
- `vector_store.py`：Milvus Lite 的薄封装。集合在首次使用时创建。支持 HNSW 索引和 IVFFlat。
- `document_loader.py`：加载 Markdown 文件，按 Markdown 标题结构分块，然后按 token 数量加重叠分块。

## 安全规则（关键）

1. **SQL 校验器**（`sql_validator.py`）：每次执行 SQL **之前**必须调用。阻止：DROP、DELETE、INSERT、UPDATE、ALTER、TRUNCATE、CREATE、EXECUTE、CALL。强制 LIMIT 上限（最大 200）。
2. **脚本执行器**（`script_executor.py`）：将脚本路径解析到 `scripts/approved/` 目录 — 阻止路径穿越。30 秒超时。输出截断 5000 字符。
3. **敏感信息**：Config service 使用 Fernet（AES-128）加密 SQLite 中的密码/API 密钥。密钥从环境变量派生。切勿记录敏感信息。

## 开发命令

```bash
# 启动开发服务器（热重载）
uvicorn ops_agent.api.main:app --reload --port 8080

# 运行测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_intent.py -v
pytest tests/test_text2sql.py -v
```

## 关键约定

- **导入风格**：在 `ops_agent` 包内使用相对导入（例如 `from ..core import orchestrator`）
- **错误处理**：从 `utils/exceptions.py` 中抛出特定异常。API 路由捕获并返回结构化错误响应
- **流式传输**：使用 `StreamingResponse` + `text/event-stream`。生成器产出 `data: ...\n\n` 格式的 SSE 事件
- **配置**：配置由数据库驱动（非环境变量）。`config/settings.py` 存放系统级设置（路径、默认值）
- **日志**：全程使用 Loguru `logger`，不使用 `print` 或 `logging`
- **类型注解**：所有函数签名和数据类必须有完整的类型注解
