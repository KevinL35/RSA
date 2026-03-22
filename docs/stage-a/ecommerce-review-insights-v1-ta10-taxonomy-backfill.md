# TA-10 词典回灌机制（含版本化与操作日志）

## 文档信息

- 项目：电商评论情感与痛点分析系统
- 对应任务：`TA-10`
- 版本：`v1.0`
- 状态：`frozen`
- 上游：`TA-6` 词条结构、`TA-9` 候选 JSONL；审核人产出**决策 JSONL**
- 相关代码：`ml/scripts/taxonomy_backfill_lib.py`、`publish_taxonomy_backfill.py`、`rollback_taxonomy_overlay.py`

## 1. 目标

实现「**候选 → 人工复核 → 发布 / 回滚**」闭环，并留下**可追踪版本与审计记录**：

- **发布**：将 `approve` 决策合并进对应垂直的 **overlay YAML**（不直接改 seed），并递增 overlay 的 `version` 补丁位。
- **回滚**：用发布前生成的**快照文件**覆盖当前 overlay。
- **日志**：追加 JSONL 审计（默认 `ml/reports/taxonomy_backfill_audit.jsonl`，目录常被 `.gitignore`；可通过 `--audit-log` 改到受控路径）。

## 2. 垂直与文件

| vertical_id | overlay 文件（`ml/configs/`） |
|-------------|-------------------------------|
| `general` | `taxonomy_dictionary_general_overlay_v1.yaml`（TA-10 新增，初始 `entries: []`） |
| `electronics` | `taxonomy_dictionary_electronics_overlay_v1.yaml`（既有） |

合并规则与 TA-6 一致：**seed + overlay**，同一 `(dimension_6way, canonical)` 以 overlay 为准。

API `GET /api/v1/dictionary/taxonomy-preview` 已通过 `taxonomy_yaml.load_merged_entries_for_vertical` 反映 **general 的 overlay**；分析服务 `POST /analyze` 按请求体 `dictionary_vertical_id` 加载相同合并结果（未设置 `TAXONOMY_YAML` 时）。

## 3. 决策 JSONL 格式（每行一个 JSON）

### 3.1 `approve`（写入词典）

必填：

- `decision`: `"approve"`
- `vertical_id`: `"general"` 或 `"electronics"`
- `dimension_6way`: TA-1 六维之一
- `canonical`: 规范词（≥2 字符）
- `reviewer`: 审核人标识

建议（审计/溯源）：

- `batch_id`、`source_topic_id`（来自 TA-9）
- `reviewed_at`：ISO-8601 UTC
- `aliases`：字符串数组
- `priority` / `weight`：默认 `50` / `1.0`

发布后 YAML 中会附加 `entry_source: bertopic` 与 `provenance` 对象；归因引擎忽略额外字段，不影响匹配。

### 3.2 `reject` / `hold`

必填：`decision`、`vertical_id`、`reviewer`。可选 `notes`。不修改 overlay。

## 4. 命令

在**仓库根目录**执行（需已安装 `pyyaml`，与 `ml` 其他脚本一致）：

```bash
# 预览（不写文件）
python ml/scripts/publish_taxonomy_backfill.py \
  --decisions path/to/decisions.jsonl \
  --dry-run

# 发布（默认先快照到 ml/artifacts/taxonomy_snapshots/）
python ml/scripts/publish_taxonomy_backfill.py \
  --decisions path/to/decisions.jsonl

# 回滚
python ml/scripts/rollback_taxonomy_overlay.py \
  --vertical general \
  --snapshot ml/artifacts/taxonomy_snapshots/general_overlay_20250322T120000Z.yaml
```

常用参数：

- `--skip-snapshot`：本地试验跳过快照（不推荐生产）。
- `--audit-log` / `--snapshots-dir`：自定义审计与快照目录。

## 5. 审计 JSONL 字段摘要

- `publish`：单次垂直发布，`approved_merged`、`entries_before` / `after`、`overlay_version`、`snapshot_path`。
- `publish_batch_summary`：同一决策文件处理结束一行，`reject_count`、`hold_count`、`approve_verticals`。
- `rollback`：`snapshot_path`、`entries_restored` 等。

## 6. 与 TA-9 的衔接

1. 运行 `run_bertopic_offline.py` 得到 `bertopic_candidates_{batch_id}.jsonl`。
2. 人工补全 `dimension_6way`、必要时改写 `canonical` / `aliases`，并写上 `decision` / `reviewer`，保存为决策 JSONL（可与候选分列存放，也可在同仓库 `ml/reviews/` 自建目录管理）。
3. 执行 `publish_taxonomy_backfill.py`。
4. 分析服务需 `POST /admin/reload-taxonomy` 或重启进程以清空词典缓存（若未使用 `TAXONOMY_YAML` 覆盖）。

## 7. 版本与变更

- 变更合并规则或垂直列表时：同步 `taxonomy_backfill_lib.ALLOWED_VERTICALS`、`apps/analysis-service/app/taxonomy_config.py` 与本文档。
- overlay 的 `taxonomy_id` 语义不变时，仅升 `version` 补丁位即可；破坏性重命名需另发迁移说明。
