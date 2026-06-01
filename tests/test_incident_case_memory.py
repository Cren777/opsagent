from pathlib import Path

from ops_agent.models.troubleshooting.case_memory import IncidentCaseMemory


def test_case_memory_returns_high_confidence_match_for_same_log_pattern(tmp_path: Path):
    memory = IncidentCaseMemory(db_path=tmp_path / "cases.db")
    memory.save_case(
        query="nginx 502 Connection refused",
        answer="历史处理方案：重启 upstream app 服务并检查 8080 监听。",
        symptoms=["nginx", "502", "Connection refused", "upstream"],
        root_cause="upstream 服务未监听端口",
        solution="重启 app 服务",
        evidence=["connect() failed (111: Connection refused)"],
        status="resolved",
    )

    match = memory.find_similar(
        query="web-01 nginx 返回 502，日志里 connect() failed Connection refused",
        symptoms=["nginx", "502", "Connection refused"],
    )

    assert match is not None
    assert match["score"] >= 0.88
    assert "重启 upstream app 服务" in match["answer"]


def test_case_memory_ignores_low_confidence_match(tmp_path: Path):
    memory = IncidentCaseMemory(db_path=tmp_path / "cases.db")
    memory.save_case(
        query="mysql replication delay",
        answer="检查主从复制延迟。",
        symptoms=["mysql", "replication", "delay"],
        root_cause="binlog apply slow",
        solution="检查 slave sql thread",
        evidence=[],
        status="resolved",
    )

    match = memory.find_similar(
        query="nginx 502 Connection refused",
        symptoms=["nginx", "502", "Connection refused"],
    )

    assert match is None


def test_case_memory_filters_by_query_category_status_and_symptom(tmp_path: Path):
    memory = IncidentCaseMemory(db_path=tmp_path / "cases.db")
    memory.save_case(
        query="nginx 502 upstream refused",
        answer="restart upstream",
        symptoms=["nginx", "502", "Connection refused"],
        status="resolved",
        category="Nginx/错误日志",
    )
    memory.save_case(
        query="mysql too many connections",
        answer="increase max connections",
        symptoms=["mysql", "connections"],
        status="auto_saved",
        category="MySQL/连接",
    )

    result = memory.list_cases(
        query="upstream",
        category="Nginx/错误日志",
        status="resolved",
        symptom="Connection refused",
    )

    assert len(result) == 1
    assert result[0]["query"] == "nginx 502 upstream refused"


def test_case_categories_can_be_managed_and_delete_uncategorizes_cases(tmp_path: Path):
    memory = IncidentCaseMemory(db_path=tmp_path / "cases.db")
    saved = memory.save_case(
        query="nginx 502",
        answer="restart upstream",
        symptoms=["nginx", "502"],
        status="resolved",
        category="Nginx/错误日志",
    )

    memory.create_category("Nginx/错误日志")
    memory.set_category_pinned("Nginx/错误日志", True)
    deleted = memory.delete_category("Nginx/错误日志")
    item = memory.get_case(saved["case_id"])

    assert deleted is True
    assert item["category"] == ""
