-- 已生效六维词典（seed 全局 + 各垂直 overlay）；API / rsa-model-api 读路径以本表为准（种子可用 scripts/seed_taxonomy_yaml_to_supabase.py 从 ml/fixtures/taxonomy/ 导入）。
CREATE TABLE IF NOT EXISTS public.taxonomy_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_layer TEXT NOT NULL CHECK (source_layer IN ('seed', 'overlay')),
  dictionary_vertical_id TEXT NOT NULL,
  dimension_6way TEXT NOT NULL,
  canonical TEXT NOT NULL,
  canonical_norm TEXT NOT NULL,
  aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
  weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  priority INTEGER NOT NULL DEFAULT 50,
  entry_source TEXT,
  provenance JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT taxonomy_entries_seed_vertical_ck CHECK (
    (source_layer = 'seed' AND dictionary_vertical_id = 'general')
    OR source_layer = 'overlay'
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_taxonomy_entries_seed_dim_canon
  ON public.taxonomy_entries (dimension_6way, canonical_norm)
  WHERE source_layer = 'seed';

CREATE UNIQUE INDEX IF NOT EXISTS uniq_taxonomy_entries_overlay_dim_canon
  ON public.taxonomy_entries (dictionary_vertical_id, dimension_6way, canonical_norm)
  WHERE source_layer = 'overlay';

CREATE INDEX IF NOT EXISTS idx_taxonomy_entries_layer_vertical
  ON public.taxonomy_entries (source_layer, dictionary_vertical_id);

ALTER TABLE public.taxonomy_entries ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.taxonomy_entries IS 'Published taxonomy: seed rows (layer=seed, vertical=general) + per-vertical overlay; merged read = seed then overlay override same (dimension, canonical)';
