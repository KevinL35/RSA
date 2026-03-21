-- 洞察任务绑定词典垂直（类目）：general 兜底，electronics 等一级垂直可叠加专用词条

ALTER TABLE public.insight_tasks
  ADD COLUMN IF NOT EXISTS dictionary_vertical_id TEXT NOT NULL DEFAULT 'general';

COMMENT ON COLUMN public.insight_tasks.dictionary_vertical_id IS
  '词典类目：general=通用兜底，electronics=电子产品等；分析请求会随任务传给分析服务';

CREATE INDEX IF NOT EXISTS idx_insight_tasks_dictionary_vertical
  ON public.insight_tasks (dictionary_vertical_id);
