from pathlib import Path

import pytest

pytest.importorskip("loguru")

from ops_agent.models.rag.log_parser import LogParser


def test_log_parser_detects_level_without_name_error():
    parser = LogParser()

    assert parser._detect_level("connection failed") == "ERROR"
    assert parser._detect_level("warning threshold reached") == "WARNING"
    assert parser._detect_level("normal startup") == "INFO"


def test_log_parser_parse_file_handles_unmatched_lines(tmp_path: Path):
    log_file = tmp_path / "sample.log"
    log_file.write_text("plain ERROR line\n", encoding="utf-8")

    entries = LogParser().parse_file(str(log_file))

    assert len(entries) == 1
    assert entries[0].level == "ERROR"
