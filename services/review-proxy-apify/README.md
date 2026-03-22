# Apify 评论薄代理（对接 RSA TB-2）

**可选**：RSA 已支持 **`REVIEW_PROVIDER_MODE=apify`** + `APIFY_*`，可不再部署本服务（见 `docs/runbooks/apify-amazon-reviews.md`）。若希望 **Apify Token 与主 API 进程隔离**、或统一多语言网关，可继续用本代理。

RSA 的 `POST .../fetch-reviews` 会请求 **`REVIEW_PROVIDER_URL`**，body 为：

```json
{ "platform": "amazon", "product_id": "<ASIN>" }
```

本服务提供 **`POST /fetch`**，把请求转成 Apify 的 **`run-sync-get-dataset-items`**，并把 Dataset 行映射为 RSA 能吃的字段（`raw_text` 等）。

## 你需要做的

### 1. Apify

- 注册账号，在商店选好 **Amazon Reviews** 类 Actor，**手动跑通一次**，看 Dataset 里评论正文在哪个字段（常见：`reviewText`、`text`）。
- 复制 **API Token**，记下 **Actor ID**（`用户名~Actor名`）。

### 2. 配置本服务

```bash
cd services/review-proxy-apify
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env：APIFY_TOKEN、APIFY_ACTOR_ID
```

若 Actor 的 Input 用 **商品 URL** 而不是 `asins`，设：

```env
APIFY_INPUT_STYLE=productUrls
```

（环境变量名为 `productUrls`，值里写 `productUrls` 小写 u。）

### 3. 启动

```bash
uvicorn main:app --host 0.0.0.0 --port 8090
```

生产环境建议前面加 HTTPS 与鉴权：设置 **`REVIEW_PROXY_API_KEY`**，则请求必须带：

`Authorization: Bearer <与密钥一致>`

### 4. 接上 RSA

`apps/platform-api/.env`：

```env
REVIEW_PROVIDER_MOCK=false
REVIEW_PROVIDER_URL=http://127.0.0.1:8090/fetch
REVIEW_PROVIDER_API_KEY=<与 REVIEW_PROXY_API_KEY 相同，若已设置>
REVIEW_PROVIDER_TIMEOUT_SECONDS=300
```

若代理在另一台机器，把 URL 换成可访问的内网/公网地址。**勿**把 Apify Token 写进 RSA，只写代理地址与（可选）代理自己的 Bearer。

### 5. 验证

- `curl -s http://127.0.0.1:8090/healthz`
- 创建洞察任务后：`POST /api/v1/insight-tasks/{id}/fetch-reviews`（需 `X-RSA-Role: operator`）。

## 限制说明

- Apify **同步接口**最长约 **300s**；大 ASIN、多评论可能超时，需减小 `APIFY_MAX_REVIEWS` 或换异步 Run + 轮询（本仓库未内置）。
- 不同 Actor 的 **Input 字段名**可能不同；若 `asins` / `productUrls` 都不匹配，需要 fork 本服务改 `_build_apify_input`，或换用契约已对齐的供应商。

## 与「可替换供应商」的关系

以后要换非 Apify 的源：可部署**另一个**实现同样 **`POST /fetch` 契约**的服务，只改 **`REVIEW_PROVIDER_URL`**，RSA 无需改代码。
