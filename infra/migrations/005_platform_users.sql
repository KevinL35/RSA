-- 平台用户（登录与菜单权限）；后端使用 service role 访问

CREATE TABLE IF NOT EXISTS public.platform_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
  menu_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_users_status ON public.platform_users (status);

ALTER TABLE public.platform_users ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.platform_users IS 'Platform login users; menu_keys JSON array of menu keys; backend only';

-- 默认管理员 admin / admin（bcrypt）；首次部署后请修改密码
INSERT INTO public.platform_users (username, password_hash, status, menu_keys)
VALUES (
  'admin',
  '$2b$12$ogCVFZuYrlHwt7RAPTEkeeIEafK2Op96WwPTddzJ9AY3Q94L9kUTG',
  'active',
  '["insight","compare","smart-mining","dictionary","api-config","audit-log","account-permissions"]'::jsonb
)
ON CONFLICT (username) DO NOTHING;
