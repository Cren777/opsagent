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
