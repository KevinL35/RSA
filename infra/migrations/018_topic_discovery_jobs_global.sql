-- 主题挖掘任务支持「全局」（跨任务）模式：insight_task_id 可空

ALTER TABLE public.topic_discovery_jobs
  ALTER COLUMN insight_task_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_topic_jobs_global_created
  ON public.topic_discovery_jobs (created_at DESC)
  WHERE insight_task_id IS NULL;
