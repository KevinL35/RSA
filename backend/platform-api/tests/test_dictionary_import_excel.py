"""词典 Excel 导入：表头解析与行校验。"""

from io import BytesIO

from openpyxl import Workbook

from app.modules.dictionary.import_dictionary_excel import parse_dictionary_excel_rows


def _xlsx_bytes(headers: list[str], rows: list[tuple[object, ...]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(list(r))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_dictionary_excel_happy_path() -> None:
    content = _xlsx_bytes(
        ["六维维度", "规范词", "同义词"],
        [
            ("cons", "battery life", "dies fast;poor battery"),
            ("pros", "fast ship", "quick delivery"),
        ],
    )
    rows, errs = parse_dictionary_excel_rows(content, filename="d.xlsx")
    assert not errs
    assert len(rows) == 2
    assert rows[0]["dimension_6way"] == "cons"
    assert rows[0]["canonical"] == "battery life"
    assert rows[0]["aliases"] == ["dies fast", "poor battery"]
    assert rows[1]["aliases"] == ["quick delivery"]


def test_parse_dictionary_excel_missing_column() -> None:
    content = _xlsx_bytes(["规范词", "同义词"], [("x", "y")])
    rows, errs = parse_dictionary_excel_rows(content, filename="d.xlsx")
    assert not rows
    assert any("六维" in e or "dimension" in e for e in errs)


def test_parse_dictionary_excel_bad_dimension_row_skipped() -> None:
    content = _xlsx_bytes(
        ["六维维度", "规范词", "同义词"],
        [("not_a_dim", "foo", "bar")],
    )
    rows, errs = parse_dictionary_excel_rows(content, filename="d.xlsx")
    assert not rows
    assert errs
