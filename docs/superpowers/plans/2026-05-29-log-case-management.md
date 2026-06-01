# 日志与案例管理改造实施计划

> **给后续执行 Agent 的说明：** 实施本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，并按任务逐项勾选执行。所有步骤都使用 checkbox（`- [ ]`）格式，便于追踪进度。

**目标：** 让 OpsAgent 能识别并分析当前已保存、新产生、用户上传的日志文件，同时把“日志与案例”页面改造成便于分类、筛选、定位和复用的管理工作台。

**架构思路：** 后端把日志来源统一成一个日志目录服务：用户上传日志、项目运行日志 `logs/`、历史样例日志 `data/logs/` 都会被发现并生成可查询的 metadata。聊天编排在故障排查前，根据用户提到的文件名自动匹配日志并注入诊断上下文。前端从“两个平铺表格”改为“左侧分类树 + 顶部统计筛选 + 主列表 + 详情抽屉”的工作台，分类从手输文本升级为可筛选、可聚合、可批量调整的管理属性。

**技术栈：** Python 3.11 / FastAPI / Pydantic、现有 `LogUploadService`、`Orchestrator`、Vue 3 / TypeScript / Element Plus / Pinia、pytest、vue-tsc。

---

## 文件结构

- 修改 `config/settings.py`
  - 新增明确的日志来源配置：`runtime_logs_dir`、`seed_logs_dir`，保留 `uploaded_logs_dir`。
- 修改 `ops_agent/models/uploads/log_upload_service.py`
  - 把服务改造成统一日志目录服务，既管理上传日志，也发现本地已有日志。
  - 增加文件名搜索、metadata 自动同步、来源标记、允许目录内的安全预览。
- 修改 `ops_agent/api/routes/uploads.py`
  - 保留聊天上传接口，增加可选 `category` 参数，返回规范化 metadata。
- 修改 `ops_agent/api/routes/incidents.py`
  - 给日志和案例列表增加查询/筛选参数。
  - 增加分类聚合接口。
  - 保持旧路由兼容。
- 修改 `ops_agent/core/orchestrator.py`
  - 在路由到故障排查前，把用户提到的日志文件名解析为日志目录项。
  - 合并自动解析出的日志附件和用户显式上传的附件。
- 修改 `ops_agent/core/intent/classifier.py`
  - 继续保证 `.log` 文件名请求被识别为 `fault_troubleshooting`。
  - 增加 `ops_agent_YYYY-MM-DD.log` 相关测试。
- 修改 `ops_agent/models/indexing/index_service.py`
  - 默认重建日志索引时，从所有日志目录来源重建，而不是只看 `data/logs`。
- 修改 `frontend/src/types/incident.ts`
  - 扩展日志/案例类型字段：`source`、`path`、`mtime`、`tags`、`category`、`severity`、`status`。
- 修改 `frontend/src/api/incidents.ts`
  - 增加类型化查询参数和分类统计接口。
- 修改 `frontend/src/api/upload.ts`
  - 支持从“日志与案例”页面上传日志，并携带分类信息。
- 重写 `frontend/src/views/LogsCasesView.vue`
  - 用管理工作台替换当前 tab + 表格页面。
- 新增或修改测试：
  - `tests/test_log_upload_service.py`
  - `tests/test_chat_attachments_contract.py`
  - `tests/test_intent.py`
  - `tests/test_management_services.py`

---

### 任务 1：统一日志存储与发现

**涉及文件：**
- 修改：`config/settings.py`
- 修改：`ops_agent/models/uploads/log_upload_service.py`
- 测试：`tests/test_log_upload_service.py`

- [ ] **步骤 1：先写失败测试，证明运行日志和样例日志能被发现**

在 `tests/test_log_upload_service.py` 中增加测试，证明 `logs/` 和 `data/logs/` 下的日志不需要手动上传，也能出现在 `list_logs()` 结果中：

```python
def test_list_logs_discovers_runtime_and_seed_logs(tmp_path: Path):
    upload_root = tmp_path / "uploads"
    runtime_root = tmp_path / "runtime"
    seed_root = tmp_path / "seed"
    runtime_root.mkdir()
    seed_root.mkdir()
    (runtime_root / "ops_agent_2026-05-25.log").write_text("ERROR runtime failure\n", encoding="utf-8")
    (seed_root / "syslog_sample.log").write_text("WARNING sample warning\n", encoding="utf-8")

    service = LogUploadService(
        base_dir=upload_root,
        source_dirs=[runtime_root, seed_root],
    )

    names = [item["filename"] for item in service.list_logs()]
    assert "ops_agent_2026-05-25.log" in names
    assert "syslog_sample.log" in names
```

- [ ] **步骤 2：运行失败测试**

运行：

```bash
pytest tests/test_log_upload_service.py::test_list_logs_discovers_runtime_and_seed_logs -q
```

预期：测试失败，因为当前 `LogUploadService` 只读取上传日志的 metadata JSON。

- [ ] **步骤 3：增加日志来源配置**

在 `config/settings.py` 中加入：

```python
runtime_logs_dir: str = str(PROJECT_ROOT / "logs")
seed_logs_dir: str = str(PROJECT_ROOT / "data" / "logs")
uploaded_logs_dir: str = str(PROJECT_ROOT / "data" / "uploads" / "logs")
```

- [ ] **步骤 4：在 `LogUploadService` 中增加目录发现能力**

实现以下方法和参数：

```python
def __init__(
    self,
    base_dir: str | Path | None = None,
    max_bytes: int = 20 * 1024 * 1024,
    source_dirs: list[str | Path] | None = None,
):
    self.base_dir = Path(base_dir or self._default_base_dir())
    self.source_dirs = [Path(p) for p in (source_dirs or self._default_source_dirs())]
    ...

def list_logs(self, query: str = "", category: str = "", source: str = "", severity: str = "") -> list[dict[str, Any]]:
    uploaded = self._list_uploaded_logs()
    discovered = self._discover_source_logs()
    merged = self._merge_by_identity(uploaded + discovered)
    return self._filter_logs(merged, query=query, category=category, source=source, severity=severity)

def _discover_source_logs(self) -> list[dict[str, Any]]:
    items = []
    for root in self.source_dirs:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.allowed_suffixes:
                items.append(self._metadata_from_existing_file(path, root))
    return items
```

发现到的本地文件要使用稳定 `file_id`，例如 `local_<sha1-resolved-path>`。这样预览、分类更新、索引重建都能稳定定位同一个文件。删除本地发现的运行日志时，默认只删除 metadata 覆盖记录，不物理删除 `logs/`、`data/logs/` 下的文件。

- [ ] **步骤 5：保留用户对本地发现日志设置的分类**

把分类覆盖信息保存到 `metadata/local_<hash>.json`：

```python
{
  "file_id": "local_abcd",
  "filename": "ops_agent_2026-05-25.log",
  "stored_path": "E:/ty/opsagent/logs/ops_agent_2026-05-25.log",
  "source": "runtime",
  "category": "OpsAgent/运行日志"
}
```

- [ ] **步骤 6：运行日志服务测试**

运行：

```bash
pytest tests/test_log_upload_service.py -q
```

预期：所有日志上传测试通过，包括密钥脱敏、非法扩展名拦截、本地日志发现。

---

### 任务 2：聊天时自动解析用户提到的日志文件

**涉及文件：**
- 修改：`ops_agent/models/uploads/log_upload_service.py`
- 修改：`ops_agent/core/orchestrator.py`
- 测试：`tests/test_chat_attachments_contract.py`
- 测试：`tests/test_intent.py`

- [ ] **步骤 1：先写失败测试，证明文件名能解析为日志附件**

增加：

```python
def test_resolve_mentioned_log_file_adds_attachment(tmp_path: Path):
    log_path = tmp_path / "ops_agent_2026-05-25.log"
    log_path.write_text("ERROR mysql too many connections\n", encoding="utf-8")
    service = LogUploadService(base_dir=tmp_path / "uploads", source_dirs=[tmp_path])

    matched = service.resolve_mentioned_logs("帮我分析一下 ops_agent_2026-05-25.log 文件")

    assert len(matched) == 1
    assert matched[0]["type"] == "log"
    assert matched[0]["filename"] == "ops_agent_2026-05-25.log"
```

- [ ] **步骤 2：实现文件名提取和匹配**

在 `LogUploadService` 中增加：

```python
_LOG_NAME_RE = re.compile(r"([A-Za-z0-9_.-]+\.(?:log|txt|out|gz))", re.IGNORECASE)

def resolve_mentioned_logs(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
    wanted = {m.group(1).lower() for m in self._LOG_NAME_RE.finditer(query)}
    if not wanted:
        return []
    matches = []
    for item in self.list_logs():
        if item.get("filename", "").lower() in wanted:
            matches.append({
                "id": item["file_id"],
                "type": "log",
                "filename": item["filename"],
                "source": item.get("source", ""),
            })
    return matches[:limit]
```

- [ ] **步骤 3：在 `Orchestrator.process` 和 `process_stream` 中合并自动日志附件**

意图识别前先执行：

```python
attachments = self._merge_log_attachments(
    attachments or [],
    self.log_uploads.resolve_mentioned_logs(query),
)
intent_result = await self.classifier.classify(query)
intent = self._resolve_intent_for_attachments(intent_result.intent, attachments)
```

增加辅助方法：

```python
@staticmethod
def _merge_log_attachments(explicit: list[dict], resolved: list[dict]) -> list[dict]:
    seen = {item.get("id") for item in explicit}
    merged = list(explicit)
    for item in resolved:
        if item.get("id") not in seen:
            merged.append(item)
            seen.add(item.get("id"))
    return merged
```

- [ ] **步骤 4：加强意图识别测试**

增加测试用例：

```python
@pytest.mark.parametrize("query", [
    "帮我分析一下 ops_agent_2026-05-25.log 文件",
    "查看 error.log 里面的报错",
    "分析 /var/log/nginx/access.log",
])
def test_log_file_questions_are_fault_troubleshooting(query):
    result = IntentClassifier()._rule_classify(query.lower())
    assert result.intent == IntentType.FAULT_TROUBLESHOOTING
```

- [ ] **步骤 5：运行聊天契约与意图测试**

运行：

```bash
pytest tests/test_chat_attachments_contract.py tests/test_intent.py -q
```

预期：用户提到日志文件时会强制进入 `fault_troubleshooting`，自动解析出的日志能进入诊断证据。

---

### 任务 3：让日志索引重建跟随统一日志目录

**涉及文件：**
- 修改：`ops_agent/models/indexing/index_service.py`
- 修改：`ops_agent/models/rag/log_parser.py`
- 测试：`tests/test_management_services.py`

- [ ] **步骤 1：先写失败测试，证明默认重建会使用日志目录服务**

增加测试，mock `LogIndexer.build_index`，避免真实构建向量索引：

```python
def test_rebuild_logs_uses_catalog_sources(monkeypatch, tmp_path):
    called = []

    class FakeIndexer:
        store = type("Store", (), {"count": lambda self: 3})()
        def build_index(self, target):
            called.append(target)

    monkeypatch.setattr("ops_agent.models.rag.log_parser.LogIndexer", FakeIndexer)

    result = IndexService().rebuild_logs()

    assert result["status"] == "completed"
    assert called
```

- [ ] **步骤 2：增加多目标重建支持**

在 `IndexService.rebuild_logs` 中，当没有传入 `path` 时，使用 `LogUploadService().iter_indexable_paths()`：

```python
targets = [Path(path)] if path else LogUploadService().iter_indexable_paths()
for target in targets:
    indexer.build_index(str(target))
```

- [ ] **步骤 3：增加 `iter_indexable_paths`**

在 `LogUploadService` 中增加：

```python
def iter_indexable_paths(self) -> list[Path]:
    paths = []
    for item in self.list_logs():
        path = Path(item.get("stored_path", ""))
        if path.exists() and self._is_allowed_log_path(path):
            paths.append(path)
    return paths
```

- [ ] **步骤 4：运行管理服务测试**

运行：

```bash
pytest tests/test_management_services.py tests/test_log_parser.py -q
```

预期：索引管理仍能工作，并且默认日志索引重建不再漏掉运行日志和上传日志。

---

### 任务 4：改进日志与案例分类模型

**涉及文件：**
- 修改：`ops_agent/models/uploads/log_upload_service.py`
- 修改：`ops_agent/models/troubleshooting/case_memory.py`
- 修改：`ops_agent/api/routes/incidents.py`
- 修改：`frontend/src/types/incident.ts`
- 测试：`tests/test_incident_case_memory.py`

- [ ] **步骤 1：定义分类语义**

数据和 UI 中统一使用以下维度：

```text
source: runtime | uploaded | seed
category: 业务分类路径，例如 OpsAgent/运行日志、Nginx/访问日志、MySQL/连接
severity: critical | error | warning | info
case status: auto_saved | triaged | resolved | invalid
tags: 从症状或模式中提取的标签，例如 OOM、Permission denied、Connection refused
```

- [ ] **步骤 2：增加日志分类统计接口**

增加路由：

```python
@router.get("/logs/categories")
async def list_log_categories():
    return LogUploadService().category_summary()
```

返回格式：

```json
[
  {"name": "OpsAgent/运行日志", "count": 2, "error_count": 8, "warning_count": 0},
  {"name": "未分类", "count": 1, "error_count": 0, "warning_count": 3}
]
```

- [ ] **步骤 3：增加列表筛选参数**

修改日志列表接口：

```python
@router.get("/logs")
async def list_uploaded_logs(
    query: str = "",
    category: str = "",
    source: str = "",
    severity: str = "",
):
    return LogUploadService().list_logs(query=query, category=category, source=source, severity=severity)
```

给 `/api/incidents` 增加等价筛选：`query`、`category`、`status`、`symptom`。

- [ ] **步骤 4：增加简单确定性自动分类**

只使用确定性规则，不依赖 LLM：

```python
if filename.startswith("ops_agent_"):
    category = "OpsAgent/运行日志"
elif "nginx" in filename or "access.log" in filename or "error.log" in filename:
    category = "Nginx"
elif "mysql" in text_lower:
    category = "MySQL"
else:
    category = ""
```

用户手动设置的分类始终优先于自动分类。

- [ ] **步骤 5：运行案例和日志测试**

运行：

```bash
pytest tests/test_log_upload_service.py tests/test_incident_case_memory.py -q
```

预期：分类更新仍然安全，分类统计稳定，案例状态和分类更新仍能正常工作。

---

### 任务 5：把“日志与案例”页面重做成管理工作台

**涉及文件：**
- 修改：`frontend/src/views/LogsCasesView.vue`
- 修改：`frontend/src/api/incidents.ts`
- 修改：`frontend/src/api/upload.ts`
- 修改：`frontend/src/types/incident.ts`

- [ ] **步骤 1：替换页面视觉结构**

使用以下布局：

```text
页面头部：标题 + 刷新按钮 + 上传按钮
统计行：日志总数、错误数、警告数、未处理案例数
主体：
  左侧：来源/分类树，带数量
  中间：筛选工具栏 + 高密度列表
  右侧：详情抽屉，展示预览、模式、操作
```

- [ ] **步骤 2：增加符合用户查找习惯的筛选**

控件：

```text
搜索框：按文件名、问题、症状搜索
来源分段筛选：全部 / 运行日志 / 上传日志 / 样例日志
严重度筛选：全部 / 错误 / 警告 / 普通
分类树：点击后筛选列表
案例状态筛选：全部 / 待整理 / 已解决 / 无效
```

- [ ] **步骤 3：在该页面增加上传入口**

使用 Element Plus upload 或隐藏 file input，调用现有上传 API：

```ts
async function uploadLogs(files: File[]) {
  for (const file of files) {
    await uploadLogFile(file, { category: selectedCategory.value })
  }
  ElMessage.success('日志已上传')
  await loadAll()
}
```

- [ ] **步骤 4：用受控表单替代手输“分类”弹窗**

使用 `el-select` 或 cascader，选项来自现有分类，并支持手动创建：

```text
常用分类：
- OpsAgent/运行日志
- Nginx/访问日志
- Nginx/错误日志
- MySQL/连接
- 系统/权限
- 系统/资源
```

仍保留手动输入能力，但放到表单弹窗中，带校验和最终路径预览。

- [ ] **步骤 5：优化表格列**

日志列：

```text
文件名 | 来源 | 分类 | 严重度 | 错误/警告 | 关键模式 | 更新时间 | 操作
```

案例列：

```text
问题摘要 | 状态 | 分类 | 症状标签 | 命中证据 | 更新时间 | 操作
```

使用标签和图标，避免长文本把表格撑坏。完整内容放到详情抽屉中查看。

- [ ] **步骤 6：增加空状态和加载状态**

日志空状态：

```text
未找到日志。可上传日志，或检查 logs/ 与 data/logs/ 目录。
```

案例空状态：

```text
暂无故障案例。完成一次故障排查后会自动沉淀到这里。
```

- [ ] **步骤 7：运行前端验证**

运行：

```bash
cd frontend
npx vue-tsc -p tsconfig.app.json --noEmit
npm run build
```

预期：类型检查通过，生产构建输出到 `ops_agent/api/static/dist/`。

---

### 任务 6：端到端验收

**涉及范围：**
- 后端与前端整体验证。

- [ ] **步骤 1：后端回归测试**

运行：

```bash
pytest tests/test_log_upload_service.py tests/test_chat_attachments_contract.py tests/test_intent.py tests/test_management_services.py tests/test_incident_case_memory.py -q
```

预期：选中的后端测试全部通过。

- [ ] **步骤 2：手动聊天验收**

启动后端后，在聊天里提问：

```text
帮我分析一下 ops_agent_2026-05-25.log 文件
```

预期：

```text
intent = fault_troubleshooting
diagnostics.attachments 包含 ops_agent_2026-05-25.log
如果该文件存在于 logs/ 或 data/uploads/logs/，回答中不能再说“日志文件不存在”
```

- [ ] **步骤 3：手动页面验收**

打开“日志与案例”页面，检查：

```text
1. logs/ 下的运行日志可见。
2. 上传日志后能立即出现在列表中。
3. 修改分类后，分类树数量随之更新。
4. 搜索 ops_agent_2026-05-25.log 能缩小列表范围。
5. 预览会脱敏密钥，并展示错误数、警告数、关键模式。
6. 案例可按状态、分类、症状筛选。
```

---

## 自检

需求覆盖：
- “询问日志文件信息时不能识别当前保存日志文件”：由任务 1 和任务 2 覆盖。
- “保存逻辑只在 ops_agent 下 log 文件夹，没更新新产生文件，并且需要支持用户上传”：由任务 1、任务 3、任务 5 覆盖。
- “日志与案例 UI 太丑，分类逻辑不符合管理目标”：由任务 4 和任务 5 覆盖。

占位内容检查：
- 没有依赖 `TBD`、`TODO`、`后续补充` 等占位说明。

类型一致性检查：
- 后端返回 `file_id`、`filename`、`stored_path`、`source`、`category`、`analysis`。
- 前端类型字段与这些返回值一致，并补充 `severity`、`tags`、`status` 用于筛选和展示。
