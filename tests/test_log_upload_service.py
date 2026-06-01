from pathlib import Path

import pytest

from ops_agent.models.uploads.log_upload_service import LogUploadService


def test_save_log_file_extracts_summary_and_masks_secrets(tmp_path: Path):
    service = LogUploadService(base_dir=tmp_path)
    content = (
        b"2026/05/26 10:00:01 [error] 12#12: *9 connect() failed "
        b"(111: Connection refused) while connecting to upstream, "
        b"client: 10.0.0.8, server: api.example.com, password=super-secret\n"
        b"2026/05/26 10:00:02 [warn] 12#12: upstream timed out\n"
    )

    result = service.save_log_file("nginx-error.log", content)

    assert result["file_id"]
    assert result["filename"] == "nginx-error.log"
    assert result["analysis"]["error_count"] == 1
    assert result["analysis"]["warning_count"] == 1
    assert "Connection refused" in result["analysis"]["patterns"]
    assert "super-secret" not in result["analysis"]["summary"]
    assert "password=<redacted>" in result["analysis"]["summary"]


def test_save_log_file_rejects_unsupported_extension(tmp_path: Path):
    service = LogUploadService(base_dir=tmp_path)

    with pytest.raises(ValueError, match="不支持"):
        service.save_log_file("debug.exe", b"not a log")


def test_get_attachment_context_loads_saved_log_summary(tmp_path: Path):
    service = LogUploadService(base_dir=tmp_path)
    saved = service.save_log_file("app.log", b"ERROR Out of memory in worker\n")

    context = service.get_attachment_context([{"id": saved["file_id"], "type": "log"}])

    assert "app.log" in context
    assert "Out of memory" in context


def test_list_logs_discovers_runtime_and_seed_logs(tmp_path: Path):
    upload_root = tmp_path / "uploads"
    runtime_root = tmp_path / "runtime"
    seed_root = tmp_path / "seed"
    runtime_root.mkdir()
    seed_root.mkdir()
    (runtime_root / "ops_agent_2026-05-25.log").write_text(
        "ERROR runtime failure\n",
        encoding="utf-8",
    )
    (seed_root / "syslog_sample.log").write_text(
        "WARNING sample warning\n",
        encoding="utf-8",
    )

    service = LogUploadService(base_dir=upload_root, source_dirs=[runtime_root, seed_root])

    logs = service.list_logs()
    names = [item["filename"] for item in logs]

    assert "ops_agent_2026-05-25.log" in names
    assert "syslog_sample.log" in names
    assert {item["source"] for item in logs} == {"runtime", "seed"}


def test_resolve_mentioned_log_file_adds_attachment(tmp_path: Path):
    log_path = tmp_path / "ops_agent_2026-05-25.log"
    log_path.write_text("ERROR mysql too many connections\n", encoding="utf-8")
    service = LogUploadService(base_dir=tmp_path / "uploads", source_dirs=[tmp_path])

    matched = service.resolve_mentioned_logs("please analyze ops_agent_2026-05-25.log file")

    assert len(matched) == 1
    assert matched[0]["type"] == "log"
    assert matched[0]["filename"] == "ops_agent_2026-05-25.log"


def test_category_summary_counts_discovered_logs(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    (runtime_root / "ops_agent_2026-05-25.log").write_text(
        "ERROR failed\nWARNING slow\n",
        encoding="utf-8",
    )
    service = LogUploadService(base_dir=tmp_path / "uploads", source_dirs=[runtime_root])

    summary = service.category_summary()

    assert summary[0]["name"] == "OpsAgent/运行日志"
    assert summary[0]["count"] == 1
    assert summary[0]["error_count"] == 1
    assert summary[0]["warning_count"] == 1


def test_log_categories_can_be_managed_and_rename_updates_logs(tmp_path: Path):
    service = LogUploadService(base_dir=tmp_path)
    saved = service.save_log_file("mysql.log", b"ERROR mysql too many connections\n", category="MySQL/连接")

    service.create_category("Nginx/错误日志")
    service.set_category_pinned("MySQL/连接", True)
    renamed = service.rename_category("MySQL/连接", "MySQL/连接池")
    updated = service.get_metadata(saved["file_id"])
    deleted = service.delete_category("Nginx/错误日志")

    categories = service.category_summary()

    assert renamed["name"] == "MySQL/连接池"
    assert updated["category"] == "MySQL/连接池"
    assert deleted is True
    assert categories[0]["name"] == "MySQL/连接池"
    assert categories[0]["pinned"] is True
