import pytest

from src.reader import read_requests

CSV = (
    "id,channel,timestamp,raw_text\n"
    'REQ-001,Slack,2026-06-08 09:14,"line one\nline two"\n'
    "REQ-002,Telegram,2026-06-08 09:31,short\n"
    'REQ-003,Email,2026-06-08 10:02,"   "\n'
)


def test_reads_and_skips_blank(tmp_path):
    path = tmp_path / "in.csv"
    path.write_text(CSV, encoding="utf-8")
    requests = read_requests(path)
    assert [r.id for r in requests] == ["REQ-001", "REQ-002"]
    assert "line one\nline two" == requests[0].raw_text


def test_missing_columns_raises(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("id,raw_text\nREQ-1,hello\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_requests(path)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_requests("does_not_exist.csv")
