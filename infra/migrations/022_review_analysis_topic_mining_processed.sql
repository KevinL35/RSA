-- 主题挖掘去重标记：避免同一条 review_analysis 被重复送入 BERTopic

ALTER TABLE public.review_analysis
ADD COLUMN IF NOT EXISTS topic_mining_processed_at TIMESTAMPTZ;

ALTER TABLE public.review_analysis
ADD COLUMN IF NOT EXISTS topic_mining_batch_id TEXT;

CREATE INDEX IF NOT EXISTS idx_review_analysis_topic_mining_unprocessed
  ON public.review_analysis (dimension_match_status, topic_mining_processed_at)
  WHERE dimension_match_status = 'unmatched' AND topic_mining_processed_at IS NULL;

COMMENT ON COLUMN public.review_analysis.topic_mining_processed_at IS
'Timestamp when this unmatched review_analysis row was consumed by topic mining';

COMMENT ON COLUMN public.review_analysis.topic_mining_batch_id IS
'Batch id that consumed this row in topic mining';
