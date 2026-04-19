-- 主题挖掘任务（后台 + 状态表）：用于异步触发 bertopic_supabase_pools.py 并跟踪进度

CREATE TABLE IF NOT EXISTS public.topic_discovery_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_task_id UUID NOT NULL REFERENCES public.insight_tasks (id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
  embedding_model TEXT NOT NULL,
  pid INTEGER,
  pgid INTEGER,
  batch_id TEXT,
  summary JSONB,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_topic_jobs_task_created
  ON public.topic_discovery_jobs (insight_task_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_topic_jobs_status
  ON public.topic_discovery_jobs (status);

ALTER TABLE public.topic_discovery_jobs ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.topic_discovery_jobs
  IS 'Background BERTopic mining jobs per insight task; spawned by platform-api';
