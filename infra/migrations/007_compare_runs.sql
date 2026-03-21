-- 对比分析记录（服务端持久化，替代浏览器 localStorage）

CREATE TABLE IF NOT EXISTS public.compare_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform_a TEXT NOT NULL,
  product_id_a TEXT NOT NULL,
  platform_b TEXT NOT NULL,
  product_id_b TEXT NOT NULL,
  creator TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  model_id TEXT,
  model_label TEXT,
  status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
  error_message TEXT,
  result JSONB
);

CREATE INDEX IF NOT EXISTS idx_compare_runs_created_at ON public.compare_runs (created_at DESC);

ALTER TABLE public.compare_runs ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.compare_runs IS 'Product compare runs; FastAPI uses service role (bypasses RLS)';
