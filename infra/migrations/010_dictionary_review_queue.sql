-- 词典审核待办队列（BERTopic/导入管线写入；FastAPI service role 读写）
CREATE TABLE IF NOT EXISTS public.dictionary_review_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind TEXT NOT NULL CHECK (kind IN ('new_discovery', 'existing')),
  canonical TEXT NOT NULL,
  synonyms JSONB NOT NULL DEFAULT '[]'::jsonb,
  dictionary_vertical_id TEXT NOT NULL DEFAULT 'general',
  dimension_6way TEXT,
  batch_id TEXT,
  source_topic_id TEXT,
  quality_score REAL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'withdrawn')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dictionary_review_queue_pending_created
  ON public.dictionary_review_queue (created_at ASC)
  WHERE status = 'pending';

ALTER TABLE public.dictionary_review_queue ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.dictionary_review_queue IS 'Pending dictionary review rows; insert via jobs/service role; UI lists status=pending';

-- 手工验收入列示例（SQL Editor）：
-- INSERT INTO public.dictionary_review_queue (kind, canonical, synonyms, dictionary_vertical_id, dimension_6way, batch_id, source_topic_id)
-- VALUES (
--   'new_discovery',
--   'battery life',
--   '["runs out fast", "dies quickly"]'::jsonb,
--   'general',
--   'cons',
--   'batch-demo-1',
--   'topic-42'
-- );
