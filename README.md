# Intelligent Data Analysis System

## 环境要求

| 组件 | 版本（参考） |
|------|----------------|
| Python | 3.11+ |
| Node.js | 20+ |

## 后端（FastAPI）

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 健康检查：<http://127.0.0.1:8000/health>，期望 `{"status":"ok"}`。
- **Phase 2（API）**：需配置 `DASHSCOPE_API_KEY`（或 `OPENAI_API_KEY`）后，NL2SQL 才会真正调用模型；默认 `AUTH_DEMO_MODE=true` 时 `POST /api/auth/login` 任意账号均可换取 JWT。
  - `POST /api/auth/login` → `access_token`
  - `GET|POST|PATCH|DELETE /api/sessions` 会话 CRUD
  - `GET /api/sessions/{id}/messages` 消息列表
  - `POST /api/sessions/{id}/messages` 同步问答，响应含 `reply`、`sql`、`data`（`columns`/`rows`）、`meta`
  - `POST /api/sessions/{id}/messages/stream` SSE（`event: step` / `event: final`，final 与同步 JSON 形状一致）
  - 元数据与会话消息存 `backend/data/metadata.db`，分析示例库 `backend/data/analytics.db`（启动时自动建表与种子数据）。
- 测试：

```bash
cd backend
pytest
```

- NL2SQL + Qwen 实测（需 `DASHSCOPE_API_KEY`）：`python scripts/test_nl2sql_qwen_output.py`（输出 Agent 真实 `messages` / `tool_calls` 结构，见 `docs/Phase2-开发规范.md` 7.6 节）。

## 前端（Vite + React + TypeScript）

```bash
cd frontend
npm install
npm run dev
```

- 开发地址：<http://127.0.0.1:5173>（见 `frontend/vite.config.ts`；若端口占用，终端会提示实际端口）。
- **Phase 3（联调）**：先启动后端（默认 `8000`），再 `npm run dev`。未设置 `VITE_API_BASE_URL` 时，浏览器请求走相对路径 `/api`，由 Vite 代理到 `http://127.0.0.1:8000`。登录页调用 `POST /api/auth/login`，将返回的 `access_token` 存入 `localStorage`；工作区走真实会话与消息接口，**JSON 字段与后端一致（snake_case）**：`SessionOut` 的 `created_at` / `updated_at`，`MessageOut` 的 `meta.sql` / `meta.data.columns` / `meta.data.rows`，发消息响应的 `reply` / `sql` / `data` / `meta`。右侧柱状图由 `data.columns` 与 `data.rows` 推导类别轴与数值轴。
- 可选：复制 `frontend/.env.example` 为 `.env`，按需填写 `VITE_API_BASE_URL`（例如直连后端 origin）。
- 测试：

```bash
cd frontend
npm run test
```

## 仓库结构

```
backend/    # FastAPI 应用
frontend/   # React 前端
docs/       # 需求与文档（含 Phase 2：[Phase2-开发规范.md](docs/Phase2-开发规范.md)）
```
