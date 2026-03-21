-- 商品快照（Pangolin amzProductDetail 等）：标题、主图、展示价，供列表展示
ALTER TABLE public.insight_tasks
  ADD COLUMN IF NOT EXISTS product_snapshot JSONB;

COMMENT ON COLUMN public.insight_tasks.product_snapshot IS
  'Product metadata snapshot (title, image_url, price_display); written on fetch-reviews when provider supplies it';
