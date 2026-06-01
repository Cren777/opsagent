from pathlib import Path

from ops_agent.models.knowledge.knowledge_service import KnowledgeService
from ops_agent.models.indexing.index_service import IndexService
from ops_agent.models.tools.diagnostic_service import DiagnosticService
from ops_agent.models.troubleshooting.case_memory import IncidentCaseMemory
from ops_agent.models.uploads.log_upload_service import LogUploadService


def test_knowledge_service_saves_lists_previews_and_deletes_file(tmp_path: Path):
    service = KnowledgeService(base_dir=tmp_path)

    saved = service.save_file("linux/disk.md", b"# Disk\n\nUse df -h.")
    files = service.list_files()
    preview = service.get_file(saved["file_id"])

    assert saved["relative_path"] == "linux/disk.md"
    assert files[0]["filename"] == "disk.md"
    assert preview["content"] == "# Disk\n\nUse df -h."
    assert service.delete_file(saved["file_id"]) is True
    assert service.list_files() == []


def test_knowledge_service_creates_folders_and_returns_tree(tmp_path: Path):
    service = KnowledgeService(base_dir=tmp_path)

    folder = service.create_folder("linux/nginx")
    service.save_file("linux/nginx/restart.md", b"# Restart nginx")
    tree = service.get_tree()

    assert folder["relative_path"] == "linux/nginx"
    assert tree[0]["name"] == "linux"
    assert tree[0]["children"][0]["name"] == "nginx"
    assert tree[0]["children"][0]["files"][0]["filename"] == "restart.md"


def test_knowledge_service_renames_folder(tmp_path: Path):
    service = KnowledgeService(base_dir=tmp_path)
    service.save_file("linux_ops/disk.md", b"# Disk")

    renamed = service.rename_folder("linux_ops", "linux")
    files = service.list_files()

    assert renamed["relative_path"] == "linux"
    assert files[0]["relative_path"] == "linux/disk.md"
    assert not (tmp_path / "linux_ops").exists()


def test_knowledge_service_deletes_folder_recursively(tmp_path: Path):
    service = KnowledgeService(base_dir=tmp_path)
    service.save_file("linux_ops/disk.md", b"# Disk")

    assert service.delete_folder("linux_ops", recursive=True) is True

    assert service.list_files() == []
    assert not (tmp_path / "linux_ops").exists()


def test_knowledge_service_marks_files_indexed_after_successful_rebuild(tmp_path: Path):
    service = KnowledgeService(base_dir=tmp_path)
    service.save_file("linux_ops/disk.md", b"# Disk")

    assert service.list_files()[0]["indexed"] is False

    service.mark_indexed()

    assert service.list_files()[0]["indexed"] is True


def test_knowledge_service_rejects_path_traversal(tmp_path: Path):
    service = KnowledgeService(base_dir=tmp_path)

    try:
        service.save_file("../secret.md", b"bad")
    except ValueError as exc:
        assert "非法" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_log_upload_service_lists_and_deletes_metadata(tmp_path: Path):
    service = LogUploadService(base_dir=tmp_path)
    saved = service.save_log_file("error.log", b"ERROR Connection refused\n")

    logs = service.list_logs()

    assert logs[0]["file_id"] == saved["file_id"]
    assert logs[0]["analysis"]["error_count"] == 1
    assert service.delete_log(saved["file_id"]) is True
    assert service.list_logs() == []


def test_log_upload_service_preview_and_category(tmp_path: Path):
    service = LogUploadService(base_dir=tmp_path)
    saved = service.save_log_file("nginx/error.log", b"ERROR password=secret-token\nINFO ok\n")

    service.update_category(saved["file_id"], "nginx/web")
    preview = service.preview_log(saved["file_id"])

    assert preview["category"] == "nginx/web"
    assert "secret-token" not in preview["content"]
    assert "password=<redacted>" in preview["content"]


def test_rebuild_logs_uses_catalog_sources(monkeypatch, tmp_path: Path):
    log_path = tmp_path / "ops_agent_2026-05-25.log"
    log_path.write_text("ERROR runtime failure\n", encoding="utf-8")
    called = []

    class FakeLogService:
        def iter_indexable_paths(self):
            return [log_path]

    class FakeStore:
        def count(self):
            return 3

    class FakeIndexer:
        store = FakeStore()

        def build_index(self, target):
            called.append(target)

    monkeypatch.setattr("ops_agent.models.indexing.index_service.LogUploadService", FakeLogService)
    monkeypatch.setattr("ops_agent.models.indexing.index_service.LogIndexer", FakeIndexer)

    result = IndexService().rebuild_logs()

    assert result["status"] == "completed"
    assert called == [str(log_path)]


def test_case_memory_lists_updates_and_deletes_cases(tmp_path: Path):
    memory = IncidentCaseMemory(db_path=tmp_path / "cases.db")
    saved = memory.save_case(
        query="nginx 502",
        answer="restart app",
        symptoms=["nginx", "502"],
        status="auto_saved",
    )

    assert memory.list_cases()[0]["case_id"] == saved["case_id"]
    assert memory.update_status(saved["case_id"], "resolved") is True
    assert memory.get_case(saved["case_id"])["status"] == "resolved"
    assert memory.delete_case(saved["case_id"]) is True
    assert memory.list_cases() == []


def test_case_memory_updates_category(tmp_path: Path):
    memory = IncidentCaseMemory(db_path=tmp_path / "cases.db")
    saved = memory.save_case(
        query="nginx 502",
        answer="restart app",
        symptoms=["nginx", "502"],
        category="nginx",
    )

    assert memory.get_case(saved["case_id"])["category"] == "nginx"
    assert memory.update_category(saved["case_id"], "nginx/upstream") is True
    assert memory.get_case(saved["case_id"])["category"] == "nginx/upstream"


def test_diagnostic_service_lists_scripts_and_runs_allowed_script(tmp_path: Path):
    script = tmp_path / "check_test.py"
    script.write_text("# test script\nprint('ok')\n", encoding="utf-8")

    service = DiagnosticService(approved_dir=tmp_path)
    scripts = service.list_scripts()
    result = service.run_script("check_test.py")

    assert scripts[0]["name"] == "check_test.py"
    assert result["exit_code"] == "0"
    assert "ok" in result["stdout"]


def test_diagnostic_service_uploads_pending_and_enables_script(tmp_path: Path):
    approved = tmp_path / "approved"
    pending = tmp_path / "pending"
    service = DiagnosticService(approved_dir=approved, pending_dir=pending)

    uploaded = service.upload_script("check_custom.py", b"# custom\nprint('custom')\n")
    pending_scripts = service.list_pending_scripts()
    enabled = service.enable_script(uploaded["name"])

    assert pending_scripts[0]["name"] == "check_custom.py"
    assert enabled["status"] == "enabled"
    assert service.list_scripts()[0]["name"] == "check_custom.py"
    assert "custom" in service.preview_script("check_custom.py")["content"]
