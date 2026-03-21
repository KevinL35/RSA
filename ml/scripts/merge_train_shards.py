"""
Merge train shard CSVs into one train.csv (same columns, concat rows).

Examples:
  python ml/scripts/merge_train_shards.py \\
    --glob "ml/data/splits/train.csv.part5-*" \\
    --output ml/data/splits/train.csv

  python ml/scripts/merge_train_shards.py \\
    --glob "ml/data/splits/train.csv.part5-*" \\
    --output "ml/data/splits/train.csv" \\
    --dedupe-id
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from csv_splits import read_split_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge train CSV shards into one file.")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--glob",
        dest="glob_pat",
        help='Glob for shard files, e.g. "ml/data/splits/train.csv.part5-*"',
    )
    g.add_argument(
        "--inputs",
        nargs="+",
        help="Explicit shard paths in order (alternative to --glob).",
    )
    parser.add_argument("--output", required=True, help="Merged train.csv path.")
    parser.add_argument(
        "--dedupe-id",
        action="store_true",
        help="If column 'id' exists, drop duplicate ids (keep first).",
    )
    args = parser.parse_args()

    if args.glob_pat:
        paths = sorted(Path(p) for p in glob.glob(args.glob_pat))
    else:
        paths = [Path(p) for p in args.inputs]

    if not paths:
        raise SystemExit("No files matched; check --glob or --inputs.")

    for p in paths:
        if not p.exists():
            raise FileNotFoundError(p)

    dfs = [read_split_csv(p) for p in paths]
    df = pd.concat(dfs, ignore_index=True)

    if args.dedupe_id and "id" in df.columns:
        n0 = len(df)
        df = df.drop_duplicates(subset=["id"], keep="first")
        if len(df) < n0:
            print(f"dedupe-id: removed {n0 - len(df)} duplicate id row(s)")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
