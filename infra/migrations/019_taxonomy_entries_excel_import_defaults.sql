-- 与平台词典 Excel 导入行为对齐：后端不再从 Excel 解析权重/优先级，写入 overlay 时固定为默认 1.0 / 50。
COMMENT ON COLUMN public.taxonomy_entries.weight IS '词条权重；词典 Excel 导入固定写入 1.0。';
COMMENT ON COLUMN public.taxonomy_entries.priority IS '同维排序与匹配消歧优先级；词典 Excel 导入固定写入 50。';
