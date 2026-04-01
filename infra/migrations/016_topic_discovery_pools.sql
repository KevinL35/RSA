-- 主题挖掘三池：亮点池/痛点池/观察池

CREATE TABLE IF NOT EXISTS public.topic_pool_highlight (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id TEXT NOT NULL,
  source_sentiment TEXT NOT NULL DEFAULT 'positive',
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  source_topic_id TEXT NOT NULL,
  suggested_canonical TEXT NOT NULL,
  aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
  quality_score REAL,
  evidence_snippets JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.topic_pool_pain (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id TEXT NOT NULL,
  source_sentiment TEXT NOT NULL DEFAULT 'negative',
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  source_topic_id TEXT NOT NULL,
  suggested_canonical TEXT NOT NULL,
  aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
  quality_score REAL,
  evidence_snippets JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.topic_pool_observation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id TEXT NOT NULL,
  source_sentiment TEXT NOT NULL DEFAULT 'neutral',
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  source_topic_id TEXT NOT NULL,
  suggested_canonical TEXT NOT NULL,
  aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
  quality_score REAL,
  evidence_snippets JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_topic_pool_highlight_batch ON public.topic_pool_highlight (batch_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_topic_pool_pain_batch ON public.topic_pool_pain (batch_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_topic_pool_observation_batch ON public.topic_pool_observation (batch_id, created_at DESC);

ALTER TABLE public.topic_pool_highlight ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_pool_pain ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_pool_observation ENABLE ROW LEVEL SECURITY;
