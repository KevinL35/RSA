-- 评论原文（TB-2）：与 insight_tasks 关联，供后续分析与证据追溯

CREATE TABLE IF NOT EXISTS public.reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  external_review_id TEXT,
  raw_text TEXT NOT NULL,
  title TEXT,
  rating REAL,
  sku TEXT,
  reviewed_at TIMESTAMPTZ,
  lang TEXT,
  extra JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reviews_task_created
  ON public.reviews (insight_task_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reviews_product
  ON public.reviews (platform, product_id);

ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.reviews IS 'Raw reviews from configured fetch API; service role writes';
