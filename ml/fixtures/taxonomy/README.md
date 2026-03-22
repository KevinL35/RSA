# 六维词典 YAML 样例（种子 / overlay）

运行 **`scripts/seed_taxonomy_yaml_to_supabase.py`** 时从此目录读取，写入 **`public.taxonomy_entries`**。

线上 **`apps/platform-api`** 与 **`apps/analysis-api`** 运行时**只读 Supabase**，不再回退到仓库内 YAML。
