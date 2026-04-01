-- TB-4 扩展：三分类总表增加六维匹配状态（跨商品主题挖掘可直接按 unmatched 聚合）

ALTER TABLE public.review_analysis
ADD COLUMN IF NOT EXISTS dimension_match_status TEXT NOT NULL DEFAULT 'unknown'
CHECK (dimension_match_status IN ('matched', 'unmatched', 'unknown'));

CREATE INDEX IF NOT EXISTS idx_review_analysis_task_match_status
  ON public.review_analysis (insight_task_id, dimension_match_status);

CREATE INDEX IF NOT EXISTS idx_review_analysis_product_match_status
  ON public.review_analysis (platform, product_id, dimension_match_status);
