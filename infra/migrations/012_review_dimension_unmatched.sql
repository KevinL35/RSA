-- TB-4 扩展：六维未命中评论池（供主题挖掘/补洞任务直接消费）
-- 语义：该行表示 review_analysis 已存在，但本轮六维词典未命中任何维度。

CREATE TABLE IF NOT EXISTS public.review_dimension_unmatched (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_analysis_id UUID NOT NULL UNIQUE REFERENCES public.review_analysis (id) ON DELETE CASCADE,
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  sentiment_label TEXT NOT NULL CHECK (sentiment_label IN ('negative', 'neutral', 'positive')),
  reason TEXT NOT NULL DEFAULT 'no_dimension_hit',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rdu_task ON public.review_dimension_unmatched (insight_task_id);
CREATE INDEX IF NOT EXISTS idx_rdu_product ON public.review_dimension_unmatched (platform, product_id);
CREATE INDEX IF NOT EXISTS idx_rdu_review ON public.review_dimension_unmatched (review_id);

ALTER TABLE public.review_dimension_unmatched ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.review_dimension_unmatched IS 'Reviews with sentiment but no six-dimension hits for current analysis snapshot';
