#!/usr/bin/env python3
"""从 ml/sentiment/data/raw 随机抽样评论，生成带时间与评论列的 Excel（.xlsx）。"""

from __future__ import annotations

import argparse
import json
import random
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape


def reservoir_sample_json_reviewtext(path: Path, k: int) -> list[str]:
    reservoir: list[str] = []
    n = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = (obj.get("reviewText") or "").strip()
            if not text:
                continue
            n += 1
            if len(reservoir) < k:
                reservoir.append(text)
            else:
                j = random.randint(0, n - 1)
                if j < k:
                    reservoir[j] = text
    return reservoir


def random_datetimes(count: int, start: datetime, end: datetime) -> list[datetime]:
    delta_sec = int((end - start).total_seconds())
    return [start + timedelta(seconds=random.randint(0, delta_sec)) for _ in range(count)]


def write_xlsx_minimal(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    """不依赖 openpyxl：写入最小合法 .xlsx（单 sheet）。"""
    sheet_rows_xml: list[str] = []
    for r_idx, row in enumerate(rows, start=2):
        cells = []
        for c_idx, val in enumerate(row, start=1):
            col = ""
            n = c_idx
            while n:
                n, rem = divmod(n - 1, 26)
                col = chr(65 + rem) + col
            esc = escape(str(val), {"\n": "&#10;", "\r": ""})
            cells.append(f'<c r="{col}{r_idx}" t="inlineStr"><is><t>{esc}</t></is></c>')
        sheet_rows_xml.append(f"<row r=\"{r_idx}\">{''.join(cells)}</row>")

    header_cells = []
    for c_idx, h in enumerate(headers, start=1):
        col = ""
        n = c_idx
        while n:
            n, rem = divmod(n - 1, 26)
            col = chr(65 + rem) + col
        esc = escape(str(h), {"\n": "&#10;", "\r": ""})
        header_cells.append(f'<c r="{col}1" t="inlineStr"><is><t>{esc}</t></is></c>')
    sheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>
<row r="1">{"".join(header_cells)}</row>
{"".join(sheet_rows_xml)}
</sheetData>
</worksheet>"""

    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels_xml)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    path.write_bytes(buf.getvalue())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "ml" / "sentiment" / "data" / "raw",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "ml" / "sentiment" / "data" / "sample_excel",
    )
    args = parser.parse_args()

    raw = args.raw_dir
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = raw / "Electronics_5.json"

    total = 500 + 1000 + 2000
    if not json_path.is_file():
        raise SystemExit(f"未找到 {json_path}（当前仅从 JSONL 抽样，避免整表扫描超大 CSV）。")
    texts = reservoir_sample_json_reviewtext(json_path, total)
    if len(texts) < total:
        raise SystemExit(f"评论样本不足：需要 {total} 条，仅得到 {len(texts)}。请检查 {json_path}。")

    random.shuffle(texts)
    chunks = [texts[:500], texts[500:1500], texts[1500:3500]]

    start = datetime(2026, 2, 1, 0, 0, 0)
    end = datetime(2026, 3, 15, 23, 59, 59)
    headers = ["时间", "评论"]

    specs = [(500, "reviews_sample_500.xlsx"), (1000, "reviews_sample_1000.xlsx"), (2000, "reviews_sample_2000.xlsx")]
    offset = 0
    for (n_rows, filename), chunk in zip(specs, chunks):
        times = random_datetimes(n_rows, start, end)
        rows = [[times[i].strftime("%Y-%m-%d %H:%M:%S"), chunk[i]] for i in range(n_rows)]
        write_xlsx_minimal(out_dir / filename, headers, rows)
        print(f"写入 {out_dir / filename}（{n_rows} 行）")


if __name__ == "__main__":
    main()
