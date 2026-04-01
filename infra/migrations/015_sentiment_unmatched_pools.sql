-- TB-4 扩展：三分类总表（仅存六维未命中），用于跨商品主题挖掘

CREATE TABLE IF NOT EXISTS public.review_sentiment_positive_unmatched (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_analysis_id UUID NOT NULL UNIQUE REFERENCES public.review_analysis (id) ON DELETE CASCADE,
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT 'no_dimension_hit',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.review_sentiment_neutral_unmatched (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_analysis_id UUID NOT NULL UNIQUE REFERENCES public.review_analysis (id) ON DELETE CASCADE,
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT 'no_dimension_hit',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.review_sentiment_negative_unmatched (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_analysis_id UUID NOT NULL UNIQUE REFERENCES public.review_analysis (id) ON DELETE CASCADE,
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT 'no_dimension_hit',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rsup_task ON public.review_sentiment_positive_unmatched (insight_task_id);
CREATE INDEX IF NOT EXISTS idx_rsun_task ON public.review_sentiment_neutral_unmatched (insight_task_id);
CREATE INDEX IF NOT EXISTS idx_rsug_task ON public.review_sentiment_negative_unmatched (insight_task_id);

CREATE INDEX IF NOT EXISTS idx_rsup_product ON public.review_sentiment_positive_unmatched (platform, product_id);
CREATE INDEX IF NOT EXISTS idx_rsun_product ON public.review_sentiment_neutral_unmatched (platform, product_id);
CREATE INDEX IF NOT EXISTS idx_rsug_product ON public.review_sentiment_negative_unmatched (platform, product_id);

ALTER TABLE public.review_sentiment_positive_unmatched ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_sentiment_neutral_unmatched ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_sentiment_negative_unmatched ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.review_sentiment_positive_unmatched IS 'Positive reviews unmatched by six-dimension dictionary';
COMMENT ON TABLE public.review_sentiment_neutral_unmatched IS 'Neutral reviews unmatched by six-dimension dictionary';
COMMENT ON TABLE public.review_sentiment_negative_unmatched IS 'Negative reviews unmatched by six-dimension dictionary';
