# OpsAgent — 项目整体指南（AI Agent 使用）

## 项目简介

OpsAgent 是一个基于大语言模型的智能运维助手。它提供 RAG 知识检索、Text2SQL 自然语言数据分析、自动故障排查的闭环工作流。用户通过 Web 聊天界面用自然语言提问，完成运维查询、数据库分析和系统诊断。

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
    core/               # 编排器、意图分类、任务路由、结果融合
    models/             # LLM 客户端、RAG、Text2SQL、工具（数据源、脚本执行）
    data/               # Milvus 向量存储封装、文档加载器
    utils/              # 异常、日志
  frontend/             # Vue 3 SPA
    src/
      api/              # Axios API 客户端层
      components/       # Vue 组件（chat/、layout/、datasource/、shared/）
      router/           # Vue Router 配置
      stores/           # Pinia 状态管理
      types/            # TypeScript 类型定义
      views/            # 页面级组件
  config/               # Pydantic 设置
  data/                 # 运行时数据（SQLite、知识库、日志、数据库 schema、向量）
  scripts/              # 工具脚本（init_db、build_index、demo_scenarios）
  tests/                # pytest 测试
```

## 架构流程

1. 用户通过 Vue 聊天界面提交查询 → POST `/api/chat` 或 `/api/chat/stream`（SSE）
2. 意图分类：正则快速匹配 → LLM 精确分类
   - `knowledge_query` → RAG 流水线（Milvus 向量搜索 + LLM 融合）
   - `data_analysis` → Text2SQL（schema 探查 → LLM 生成 SQL → 安全校验 → 执行 → 总结）
   - `fault_troubleshooting` → 并行执行：RAG + Milvus 日志搜索 + 沙箱脚本 → LLM 诊断
3. 结果融合：LLM 从多源证据生成结构化回答
4. 流式输出：SSE 事件（`intent` → `token` 块 → `done` 附带元数据）

## 关键约定

- **前后端通信**：REST API（Axios ↔ FastAPI），流式聊天使用 SSE
- **构建输出**：`npm run build` 输出到 `ops_agent/api/static/dist/`，由 FastAPI 以 SPA 降级路由提供
- **开发代理**：Vite 开发服务器将 `/api` 代理到 `localhost:8080`
- **配置管理**：数据源和 LLM 提供商存储在 SQLite 中，密钥加密存储
- **脚本执行**：仅执行 `scripts/approved/` 中的脚本，30 秒超时，输出截断 5000 字符

## 开发工作流

1. 后端：`uvicorn ops_agent.api.main:app --reload --port 8080`
2. 前端：`cd frontend && npm run dev`
3. 测试：`pytest tests/`
4. 构建：`cd frontend && npm run build`，然后重启后端

## 关键安全规则

- **Text2SQL**：阻止 DROP/DELETE/INSERT/UPDATE/ALTER/TRUNCATE/CREATE — 仅允许 SELECT
- **Text2SQL**：强制 LIMIT ≤ 200
- **脚本执行器**：仅执行 `scripts/approved/` 中的脚本，不执行任意命令
- **SQLite 配置数据库**：包含加密密钥，不要提交到 git
