from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ops_agent.api.routes import config


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(config, "DATASOURCE_UPLOAD_DIR", tmp_path / "uploads", raising=False)
    app = FastAPI()
    app.include_router(config.router)
    return TestClient(app)


def test_upload_csv_datasource_file_saves_under_controlled_directory(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/config/datasources/upload-file",
        files={"file": ("report.csv", b"name,value\ncpu,95\nmem,88\n", "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["original_filename"] == "report.csv"
    assert payload["file_type"] == "csv"
    assert payload["sheet_names"] == []
    saved_path = Path(payload["file_path"])
    assert saved_path.exists()
    assert saved_path.parent.parent == tmp_path / "uploads"
    assert saved_path.read_text(encoding="utf-8") == "name,value\ncpu,95\nmem,88\n"


def test_upload_datasource_file_rejects_non_excel_csv(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/config/datasources/upload-file",
        files={"file": ("notes.txt", b"not a spreadsheet", "text/plain")},
    )

    assert response.status_code == 400
    assert "Only Excel and CSV files are supported" in response.json()["detail"]


def test_upload_datasource_file_sanitizes_dangerous_filename(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/config/datasources/upload-file",
        files={"file": ("../evil.csv", b"a,b\n1,2\n", "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    saved_path = Path(payload["file_path"])
    assert saved_path.name == "evil.csv"
    assert saved_path.parent.parent == tmp_path / "uploads"
