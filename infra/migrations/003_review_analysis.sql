-- TB-4：评论级分析结果 + 六维命中行（可按任务/商品/维度检索；review_id 反查 reviews.raw_text）

CREATE TABLE IF NOT EXISTS public.review_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  sentiment_label TEXT NOT NULL CHECK (sentiment_label IN ('negative', 'neutral', 'positive')),
  sentiment_confidence REAL,
  analysis_provider_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (insight_task_id, review_id)
);

CREATE INDEX IF NOT EXISTS idx_review_analysis_task ON public.review_analysis (insight_task_id);
CREATE INDEX IF NOT EXISTS idx_review_analysis_product ON public.review_analysis (platform, product_id);
CREATE INDEX IF NOT EXISTS idx_review_analysis_review ON public.review_analysis (review_id);

CREATE TABLE IF NOT EXISTS public.review_dimension_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_analysis_id UUID NOT NULL REFERENCES public.review_analysis (id) ON DELETE CASCADE,
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  dimension TEXT NOT NULL CHECK (
    dimension IN (
      'pros',
      'cons',
      'return_reasons',
      'purchase_motivation',
      'user_expectation',
      'usage_scenario'
    )
  ),
  keywords TEXT[] NOT NULL DEFAULT '{}',
  evidence_quote TEXT,
  highlight_spans JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rda_task ON public.review_dimension_analysis (insight_task_id);
CREATE INDEX IF NOT EXISTS idx_rda_product_dim ON public.review_dimension_analysis (platform, product_id, dimension);
CREATE INDEX IF NOT EXISTS idx_rda_review ON public.review_dimension_analysis (review_id);

ALTER TABLE public.review_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_dimension_analysis ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.review_analysis IS 'Per-review sentiment snapshot for an insight task (TB-4)';
COMMENT ON TABLE public.review_dimension_analysis IS 'Six-dimension hits with evidence; join reviews via review_id (TB-4)';
