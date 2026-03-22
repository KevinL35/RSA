# 使用 Apify「Amazon Reviews Scraper」对接 TB-2 评论抓取

本仓库的 FastAPI 会向 **`REVIEW_PROVIDER_URL`** 发 **POST**，JSON 体固定为：

```json
{ "platform": "amazon", "product_id": "<ASIN 或你存的任务 product_id>" }
```

可选请求头：`Authorization: Bearer <REVIEW_PROVIDER_API_KEY>`（与 `REVIEW_PROVIDER_API_KEY` 一致）。

响应需为 **JSON**，且能从 **顶层数组** 或 `reviews` / `items` / `data` / `results` / `records` 中取出对象列表；每条评论至少要有可被识别的正文（见 `apps/platform-api/app/integrations/review_provider/normalize.py` 中的 `raw_text` / `text` / `body` / `reviewText` 等别名）。

**Apify Actor 的 REST 接口、鉴权方式、入参字段与此不同**，不能直接把 Apify 的「Run URL」填进 `REVIEW_PROVIDER_URL` 就期望能跑通。可选：**内置 Apify**（`REVIEW_PROVIDER_MODE=apify`）、**薄代理**、或任意 **`http` 契约** 的第三方服务。

---

## 一、在 Apify 上先做的事（与是否接 RSA 无关）

1. 注册 / 登录 [apify.com](https://apify.com)。
2. 在商店打开你选的 **Amazon Reviews Scraper**（不同作者 Actor 的 **Input / 价格** 不同，选一个并订阅/付费策略符合你预期的）。
3. 在 Apify 控制台用 **手动 Run** 试跑：输入 **ASIN** 或 **商品 URL**（以该 Actor 的 Input 说明为准），确认能跑出 **Dataset** 且字段里有评论正文。
4. 打开 **Settings → Integrations / API**，复制 **API Token**（仅自己保存，勿提交 Git）。

记下该 Actor 的 ID，一般为 **`用户名~Actor 名`**（控制台 URL 或 API 文档里可见）。

---

## 二、方案 A：薄代理（推荐，不动 RSA 核心逻辑）

### 2.1 本仓库自带实现（最快落地）

目录：**[`services/review-proxy-apify`](../../services/review-proxy-apify/)**（FastAPI + Apify `run-sync-get-dataset-items`）。

按其中 **`README.md`** 操作：`APIFY_TOKEN` / `APIFY_ACTOR_ID` → 启动 `uvicorn` → 在 RSA 的 `apps/platform-api/.env` 设 `REVIEW_PROVIDER_URL=http://<代理主机>:<端口>/fetch`（及可选 `REVIEW_PROVIDER_API_KEY` 与代理的 `REVIEW_PROXY_API_KEY` 对齐）。

### 2.2 自建代理（任意语言）

若 Actor Input 与内置的 `asins` / `productUrls` 不一致，可 fork 上述服务或自写：

- 监听 `POST /fetch`，body 收 `{ "platform", "product_id" }`；
- 若 `platform === "amazon"`，把 `product_id` 当作 ASIN，按 Apify 文档拼 **Run Actor** 请求（`Authorization: Bearer <Apify Token>` 或 `?token=`）；
- 等待 Run 完成（轮询状态或 Apify 客户端的同步调用）；
- 读取 **Dataset items**，把每条映射成 RSA 能吃的字段，例如至少：
  - `raw_text` 或 `text`：评论正文（从 Apify 的 `reviewText` / `text` / `reviewDescription` 等字段拷贝过来）；
  - 可选：`rating`、`title`、`id`（作 `external_review_id`）等；
- 返回 **`{ "items": [ ... ] }`** 或 **顶层数组**。

然后把 **`REVIEW_PROVIDER_URL`** 设为该代理的地址，**`REVIEW_PROVIDER_API_KEY`** 设为代理你自己约定的 Bearer（若代理要鉴权）；Apify Token **只放在代理服务端**，不要写进前端。

---

## 三、方案 B：RSA 内置 Apify（无需薄代理）

在 `apps/platform-api/.env` 设置：

```env
REVIEW_PROVIDER_MOCK=false
REVIEW_PROVIDER_MODE=apify
APIFY_TOKEN=<Apify API Token>
APIFY_ACTOR_ID=<用户名~Actor名>
APIFY_INPUT_STYLE=asins
APIFY_MAX_REVIEWS=50
APIFY_RUN_TIMEOUT_SECONDS=240
```

- 任务 `platform` 须为 **`amazon`**，`product_id` 为 **ASIN**。若 Actor 要求商品 URL，设 `APIFY_INPUT_STYLE=productUrls`。
- 改 `.env` 后**重启** API 进程（`get_settings` 带缓存）。
- 实现位置：`app/integrations/review_provider/apify.py`。

---

## 四、本地 `.env` 占位

**内置 Apify**（方案 B）见上一节。

**薄代理**（方案 A）：

```env
REVIEW_PROVIDER_MODE=http
REVIEW_PROVIDER_URL=https://你的代理域名/fetch
REVIEW_PROVIDER_API_KEY=   # 若代理要求 Bearer，则填；否则可留空
REVIEW_PROVIDER_MOCK=false
REVIEW_PROVIDER_TIMEOUT_SECONDS=120
```

若暂未搭代理，可临时：

```env
REVIEW_PROVIDER_MOCK=true
```

仅用于联调占位数据。

---

## 五、Apify 侧参考（以官方文档为准）

- Actor Run：`POST https://api.apify.com/v2/acts/{actorId}/runs`（具体路径以 [Apify API v2](https://docs.apify.com/api/v2) 为准）。
- 鉴权：Header `Authorization: Bearer <token>` 或 Query `token`。
- Input：多为 `asins`、`productUrls`、`maxReviews` 等，**与 RSA 的 `platform`/`product_id` 不同**，必须在代理或后端适配层转换。

---

## 六、接口配置页（前端）

「评论获取 API」表格仅作 **备忘**；**真正生效**的仍是 **`apps/platform-api/.env` 的 `REVIEW_PROVIDER_*`**。代理 URL 填好后，可与表格中的名称/地址对齐记录，便于团队协作。
