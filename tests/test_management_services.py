from pathlib import Path

from ops_agent.models.knowledge.knowledge_service import KnowledgeService
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


def test_diagnostic_service_lists_scripts_and_runs_allowed_script(tmp_path: Path):
    script = tmp_path / "check_test.py"
    script.write_text("# test script\nprint('ok')\n", encoding="utf-8")

    service = DiagnosticService(approved_dir=tmp_path)
    scripts = service.list_scripts()
    result = service.run_script("check_test.py")

    assert scripts[0]["name"] == "check_test.py"
    assert result["exit_code"] == "0"
    assert "ok" in result["stdout"]
