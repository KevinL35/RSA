import argparse
from pathlib import Path

import pandas as pd
import yaml

# 超过此大小（字节）默认用分块清洗，避免一次性 read_csv 占满内存
STREAMING_THRESHOLD_BYTES = 256 * 1024 * 1024
DEFAULT_CHUNK_ROWS = 100_000


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean_chunk(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    required = cfg["required_columns"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if cfg["cleaning"]["drop_empty_text"]:
        text_col = "analysis_input_en"
        df = df[df[text_col].astype(str).str.strip() != ""]

    min_len = cfg["cleaning"]["min_text_length"]
    max_len = cfg["cleaning"]["max_text_length"]
    text_len = df["analysis_input_en"].astype(str).str.len()
    df = df[(text_len >= min_len) & (text_len <= max_len)]

    dedup_cols = cfg["cleaning"]["drop_duplicates_on"]
    df = df.drop_duplicates(subset=dedup_cols)
    return df


def clean_streaming(raw_path: Path, out_path: Path, cfg: dict, chunk_rows: int) -> tuple[int, int]:
    """分块读入、清洗、全局按 id 去重（保第一次出现）。"""
    seen: set[str] = set()
    total_in = 0
    total_out = 0
    header_written = False

    chunk_iter = pd.read_csv(raw_path, chunksize=chunk_rows, low_memory=False)

    for chunk in chunk_iter:
        total_in += len(chunk)
        chunk = clean_chunk(chunk, cfg)
        if chunk.empty:
            continue

        mask = []
        for rid in chunk["id"].astype(str):
            if rid in seen:
                mask.append(False)
            else:
                seen.add(rid)
                mask.append(True)
        chunk = chunk[mask]

        chunk.to_csv(out_path, mode="a", index=False, header=not header_written)
        header_written = True
        total_out += len(chunk)

    return total_in, total_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw sentiment dataset.")
    parser.add_argument("--config", required=True, help="Path to data contract yaml.")
    parser.add_argument(
        "--chunk-rows",
        type=int,
        default=0,
        help=f"分块行数（0=当 raw 文件 ≥{STREAMING_THRESHOLD_BYTES // (1024 * 1024)}MB 时自动启用，默认块大小 {DEFAULT_CHUNK_ROWS}）",
    )
    parser.add_argument(
        "--force-streaming",
        action="store_true",
        help="强制分块清洗（大 CSV 推荐）",
    )
    parser.add_argument(
        "--no-streaming",
        action="store_true",
        help="强制整表读入（仅适合小文件）",
    )
    args = parser.parse_args()

    cfg = load_yaml(Path(args.config))
    raw_path = Path(cfg["paths"]["raw_input"])
    out_path = Path(cfg["paths"]["cleaned_output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw file not found: {raw_path}")

    size = raw_path.stat().st_size
    use_streaming = args.force_streaming or (
        not args.no_streaming and size >= STREAMING_THRESHOLD_BYTES
    )
    chunk_rows = args.chunk_rows if args.chunk_rows > 0 else DEFAULT_CHUNK_ROWS

    if use_streaming:
        if out_path.exists():
            out_path.unlink()
        total_in, total_out = clean_streaming(raw_path, out_path, cfg, chunk_rows)
        print(f"Streaming clean: read rows (with chunks) ≈ {total_in}, wrote after dedup+filter: {total_out}")
    else:
        df = pd.read_csv(raw_path, low_memory=False)
        df = clean_chunk(df, cfg)
        df = df.drop_duplicates(subset=cfg["cleaning"]["drop_duplicates_on"])
        df.to_csv(out_path, index=False)
        total_out = len(df)
        print(f"Cleaned rows: {total_out}")

    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
