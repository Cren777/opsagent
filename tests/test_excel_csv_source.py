import sys
import types

sys.modules.setdefault(
    "loguru",
    types.SimpleNamespace(logger=types.SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)),
)

from ops_agent.models.tools.excel_source import ExcelCSVDataSource


def test_excel_csv_datasource_loads_multiple_uploaded_files(tmp_path):
    first = tmp_path / "ops_metrics.csv"
    second = tmp_path / "alert_records.csv"
    first.write_text("server,cpu\nweb-01,72.5\napp-01,95.4\n", encoding="utf-8")
    second.write_text("alert_id,level\nA-001,critical\nA-002,warning\n", encoding="utf-8")

    source = ExcelCSVDataSource(
        {
            "files": [
                {"file_path": str(first), "original_filename": "ops_metrics.csv"},
                {"file_path": str(second), "original_filename": "alert_records.csv"},
            ]
        }
    )

    assert source.get_tables() == ["ops_metrics", "alert_records"]
    assert source.get_sample_rows("ops_metrics", limit=1) == [{"server": "web-01", "cpu": 72.5}]
    assert source.get_sample_rows("alert_records", limit=1) == [{"alert_id": "A-001", "level": "critical"}]
