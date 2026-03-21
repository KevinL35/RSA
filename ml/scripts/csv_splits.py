"""Robust CSV reads for TA-4 split files (quoted text, occasional bad lines)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_split_csv(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    enc_kw: dict = {"encoding": "utf-8", "encoding_errors": "replace"}
    try:
        return pd.read_csv(path, **enc_kw)
    except pd.errors.ParserError as e:
        print(
            f"Warning: {path}: strict CSV parse failed ({e}); "
            "retrying with engine=python, on_bad_lines=skip (check data export / shards)."
        )
        return pd.read_csv(
            path,
            engine="python",
            on_bad_lines="skip",
            **enc_kw,
        )
