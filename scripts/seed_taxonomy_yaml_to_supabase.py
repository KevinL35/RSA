#!/usr/bin/env python3
"""
将 ml/fixtures/taxonomy/ 下种子与各垂直 overlay YAML 导入 public.taxonomy_entries。
需已执行 infra/migrations/011_taxonomy_entries.sql。

用法（仓库根目录，需已安装 supabase + pyyaml，且环境变量与 API 一致）：
  export SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...
  python scripts/seed_taxonomy_yaml_to_supabase.py

可选：从 apps/api/.env 加载
  set -a && source apps/api/.env && set +a && python scripts/seed_taxonomy_yaml_to_supabase.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from supabase import Client, create_client

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "ml" / "fixtures" / "taxonomy"
SEED = FIXTURES / "taxonomy_dictionary_seed_v1.yaml"


def _load_entries(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not raw or not isinstance(raw, dict):
        return []
    entries = raw.get("entries")
    if not isinstance(entries, list):
        return []
    out: list[dict] = []
    for e in entries:
        if isinstance(e, dict) and e.get("dimension_6way") and e.get("canonical"):
            out.append(e)
    return out


def _canonical_norm(canonical: str) -> str:
    return str(canonical or "").strip().lower()


def _row_overlay(vertical_id: str, e: dict) -> dict:
    dim = str(e.get("dimension_6way", "")).strip().lower()
    can = str(e.get("canonical", "")).strip()
    als = e.get("aliases")
    if not isinstance(als, list):
        als = []
    als = [str(a).strip() for a in als if str(a).strip()]
    now = datetime.now(timezone.utc).isoformat()
    prov = e.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        prov = None
    return {
        "source_layer": "overlay",
        "dictionary_vertical_id": vertical_id,
        "dimension_6way": dim,
        "canonical": can,
        "canonical_norm": _canonical_norm(can),
        "aliases": als,
        "weight": float(e.get("weight") if e.get("weight") is not None else 1.0),
        "priority": int(e.get("priority") if e.get("priority") is not None else 50),
        "entry_source": e.get("entry_source"),
        "provenance": prov,
        "created_at": now,
        "updated_at": now,
    }


def _row_seed(e: dict) -> dict:
    dim = str(e.get("dimension_6way", "")).strip().lower()
    can = str(e.get("canonical", "")).strip()
    als = e.get("aliases")
    if not isinstance(als, list):
        als = []
    als = [str(a).strip() for a in als if str(a).strip()]
    now = datetime.now(timezone.utc).isoformat()
    prov = e.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        prov = None
    return {
        "source_layer": "seed",
        "dictionary_vertical_id": "general",
        "dimension_6way": dim,
        "canonical": can,
        "canonical_norm": _canonical_norm(can),
        "aliases": als,
        "weight": float(e.get("weight") if e.get("weight") is not None else 1.0),
        "priority": int(e.get("priority") if e.get("priority") is not None else 50),
        "entry_source": e.get("entry_source") or "yaml_seed",
        "provenance": prov,
        "created_at": now,
        "updated_at": now,
    }


def _upsert(sb: Client, row: dict) -> None:
    layer = row["source_layer"]
    dim = row["dimension_6way"]
    cn = row["canonical_norm"]
    if layer == "seed":
        q = (
            sb.table("taxonomy_entries")
            .select("id")
            .eq("source_layer", "seed")
            .eq("dimension_6way", dim)
            .eq("canonical_norm", cn)
            .limit(1)
            .execute()
        )
    else:
        vid = row["dictionary_vertical_id"]
        q = (
            sb.table("taxonomy_entries")
            .select("id")
            .eq("source_layer", "overlay")
            .eq("dictionary_vertical_id", vid)
            .eq("dimension_6way", dim)
            .eq("canonical_norm", cn)
            .limit(1)
            .execute()
        )
    rows = q.data or []
    if rows:
        upd = {k: v for k, v in row.items() if k != "created_at"}
        sb.table("taxonomy_entries").update(upd).eq("id", str(rows[0]["id"])).execute()
    else:
        sb.table("taxonomy_entries").insert(row).execute()


def main() -> int:
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        print("需要环境变量 SUPABASE_URL 与 SUPABASE_SERVICE_ROLE_KEY", file=sys.stderr)
        return 1
    sb = create_client(url, key)

    seed_entries = _load_entries(SEED)
    print(f"seed: {len(seed_entries)} 条 from {SEED.relative_to(ROOT)}")
    for e in seed_entries:
        _upsert(sb, _row_seed(e))

    overlays = [
        ("general", FIXTURES / "taxonomy_dictionary_general_overlay_v1.yaml"),
        ("electronics", FIXTURES / "taxonomy_dictionary_electronics_overlay_v1.yaml"),
    ]
    for vid, path in overlays:
        ents = _load_entries(path)
        print(f"overlay {vid}: {len(ents)} 条 from {path.relative_to(ROOT)}")
        for e in ents:
            _upsert(sb, _row_overlay(vid, e))

    print("完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
