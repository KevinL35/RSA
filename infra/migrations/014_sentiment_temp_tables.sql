-- TB-4 扩展：三分类临时表（按情感拆分，供六维前后链路排查/抽样）

CREATE TABLE IF NOT EXISTS public.review_sentiment_positive_tmp (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_analysis_id UUID NOT NULL UNIQUE REFERENCES public.review_analysis (id) ON DELETE CASCADE,
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.review_sentiment_neutral_tmp (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_analysis_id UUID NOT NULL UNIQUE REFERENCES public.review_analysis (id) ON DELETE CASCADE,
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.review_sentiment_negative_tmp (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_analysis_id UUID NOT NULL UNIQUE REFERENCES public.review_analysis (id) ON DELETE CASCADE,
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  review_id UUID NOT NULL REFERENCES public.reviews (id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rsp_task ON public.review_sentiment_positive_tmp (insight_task_id);
CREATE INDEX IF NOT EXISTS idx_rsn_task ON public.review_sentiment_neutral_tmp (insight_task_id);
CREATE INDEX IF NOT EXISTS idx_rsg_task ON public.review_sentiment_negative_tmp (insight_task_id);

ALTER TABLE public.review_sentiment_positive_tmp ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_sentiment_neutral_tmp ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_sentiment_negative_tmp ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.review_sentiment_positive_tmp IS 'Temporary positive bucket per analysis run';
COMMENT ON TABLE public.review_sentiment_neutral_tmp IS 'Temporary neutral bucket per analysis run';
COMMENT ON TABLE public.review_sentiment_negative_tmp IS 'Temporary negative bucket per analysis run';
