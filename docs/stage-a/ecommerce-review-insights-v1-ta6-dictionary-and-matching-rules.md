# TA-6 六维词典种子与归因匹配规则（冻结 v1）

## 文档信息

- 任务：TA-6
- 状态：`frozen`（与 `ml/fixtures/taxonomy/taxonomy_dictionary_seed_v1.yaml` 样例同步；线上以 Supabase `taxonomy_entries` 为准）
- 六维 key：与 TA-1 一致（`pros` / `cons` / `return_reasons` / `purchase_motivation` / `user_expectation` / `usage_scenario`）

## 1. 词典条目字段

| 字段 | 说明 |
|------|------|
| `dimension_6way` | 六维之一（上表 key） |
| `canonical` | 规范痛点/标签词（写入输出的关键词主形） |
| `aliases` | 别名短语列表，参与匹配（与 canonical 等价命中，但输出关键词用 canonical） |
| `weight` | 权重（v1 引擎用于排序辅助；默认 1.0） |
| `priority` | 优先级整数，**越大越优先**；重叠命中时用于裁决 |

## 2. 匹配输入与文本规范化

- **匹配文本**：`analysis_input_en`（与 Stage A 数据契约一致）。
- **大小写**：匹配时 **大小写不敏感**（等价于对英文做 `str.lower()` 比较）。
- **证据与高亮**：`evidence_quote` 优先从 `raw_text` 中截取能覆盖命中的片段；若无法在 `raw_text` 中定位同源子串，则退化为 `analysis_input_en` 上的窗口，仍通过 `review_id` 追溯（见 TA-7 报告中的可追溯率）。

## 3. 多短语命中与重叠（冲突处理）

1. 将每条词典条目展开为若干 **模式串**：`canonical` + 每个 `aliases[]`（去重、去首尾空白）。
2. 在 `analysis_input_en` 上枚举所有模式的所有出现位置（非重叠单词边界不要求；子串匹配）。
3. **重叠定义**：两区间 `[s1, e1)` 与 `[s2, e2)` 若相交则视为重叠。
4. **裁决顺序**（与实现一致，保证可复现）：
   - 先按 **模式长度降序**（更长短语优先，避免短词「吃掉」长语义）；
   - 再按 **`priority` 降序**；
   - 再按 **起始位置 `start` 升序**。
5. **贪心选取**：按上述顺序依次尝试加入命中；若与已选集合重叠则丢弃。

说明：短词若噪声大，应通过 **更长别名** 或 **提高 priority / 删除危险短别名** 治理，而不是在引擎里硬编码停用词表（v1 保持简单）。

## 4. 输出分组（对接 TB-3 / contracts）

- 按 `dimension_6way` 分组；每组内合并本组所有命中：
  - `keywords`：命中对应的 **canonical** 去重列表（稳定排序：按首次出现顺序）。
  - `evidence_quote`：覆盖该维所有命中在 `analysis_input_en` 上的最小连续窗口，再映射到 `raw_text`（见 §2）；映射失败则用 `analysis_input_en` 窗口。
  - `highlight_spans`：`evidence_quote` 子串内的 `[start, end)` 区间（**左闭右开**），`label` 固定为 `keyword` 或与 canonical 对齐（实现见 TA-7 脚本）。

## 5. BERTopic 候选 → 词典条目（导入约定）

离线主题审核通过后，写入「拟导入词典」的行至少包含：

- `suggested_canonical`：建议规范词
- `dimension_6way`：归属维度
- `source_topic_id`：主题编号（BERTopic / 批次内唯一）
- `batch_id`：发现批次

可选：`aliases`、`quality_score`、`evidence_snippets`、`reviewer_notes`。

人工复核通过后，再转为本 YAML（或 DB）正式词条并升 `taxonomy_id` / 版本号。

## 6. 版本与变更

- 变更词典或裁决规则时：在库内更新 seed/overlay 并记录 **版本 / taxonomy_id**（灌库样例见 `ml/fixtures/taxonomy/taxonomy_dictionary_seed_v1.yaml`），并在 TA-12 类发布说明中记录。
- 本文件与仓库内种子 YAML 或库内数据不一致时，以 **已发布数据 + 本文件 §3 规则** 为执行口径；文档负责解释「为什么」。
