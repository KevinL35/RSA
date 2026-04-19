-- 洞察任务：DeepSeek 等生成的 AI 智能分析摘要（JSON），与六维看板分开更新
ALTER TABLE public.insight_tasks
  ADD COLUMN IF NOT EXISTS ai_summary JSONB;

COMMENT ON COLUMN public.insight_tasks.ai_summary IS
  'AI 洞察摘要：{ text, model, generated_at, fingerprint }，fingerprint 用于与看板数据对齐缓存';
