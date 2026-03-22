from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.modules.tasks.import_reviews_excel import parse_excel_review_rows


def _xlsx_bytes(headers: list[str], rows: list[tuple[object, object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(headers)
    for a, b in rows:
        ws.append([a, b])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_zh_headers() -> None:
    content = _xlsx_bytes(
        ["时间", "评论"],
        [
            (datetime(2026, 1, 2, 12, 0, 0), "很好"),
            ("2026-01-03", "一般"),
        ],
    )
    parsed = parse_excel_review_rows(content)
    assert len(parsed) == 2
    assert parsed[0]["raw_text"] == "很好"
    assert parsed[0]["reviewed_at"] is not None
    assert parsed[1]["raw_text"] == "一般"


def test_parse_en_headers() -> None:
    content = _xlsx_bytes(
        ["reviewed_at", "raw_text"],
        [("2026-01-01T00:00:00", "ok")],
    )
    parsed = parse_excel_review_rows(content)
    assert len(parsed) == 1
    assert parsed[0]["raw_text"] == "ok"


def test_parse_skips_empty_text() -> None:
    content = _xlsx_bytes(["时间", "评论"], [(None, "a"), (None, ""), (None, "b")])
    parsed = parse_excel_review_rows(content)
    assert [r["raw_text"] for r in parsed] == ["a", "b"]


def test_parse_missing_header() -> None:
    content = _xlsx_bytes(["foo", "bar"], [(1, "x")])
    with pytest.raises(ValueError, match="未识别表头"):
        parse_excel_review_rows(content)
