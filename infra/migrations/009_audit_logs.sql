-- 操作审计日志（账号、菜单、摘要信息；detail 存结构化补充）
CREATE TABLE IF NOT EXISTS public.audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL DEFAULT '',
  menu_key TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL,
  detail JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs (created_at DESC);

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.audit_logs IS 'Operation audit trail; FastAPI inserts via service role';
