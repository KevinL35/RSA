-- 评论洞察任务表（与 docs/plan 中 insight_tasks 概念对齐）
-- 在 Supabase SQL Editor 中执行，或通过迁移工具应用

CREATE TABLE IF NOT EXISTS public.insight_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
  analysis_provider_id TEXT,
  error_code TEXT,
  error_message TEXT,
  failure_stage TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_insight_tasks_status_created
  ON public.insight_tasks (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_insight_tasks_product
  ON public.insight_tasks (platform, product_id);

ALTER TABLE public.insight_tasks ENABLE ROW LEVEL SECURITY;

-- 服务密钥（后端 FastAPI）会绕过 RLS；若需 anon 读表请另行写 policy。
COMMENT ON TABLE public.insight_tasks IS 'Insight pipeline tasks; backend uses service role';
