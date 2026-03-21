-- 洞察任务创建人（登录用户名，由前端 X-RSA-Username 传入）

ALTER TABLE public.insight_tasks
  ADD COLUMN IF NOT EXISTS created_by TEXT;

COMMENT ON COLUMN public.insight_tasks.created_by IS
  '创建人用户名（与 platform_users.username 对齐；历史数据可为空）';

CREATE INDEX IF NOT EXISTS idx_insight_tasks_created_by ON public.insight_tasks (created_by);
