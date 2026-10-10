# Phase 2 开发规范（LLM I/O 与百炼 Qwen3-max）

本文档在 Phase 2 实现后端（FastAPI + LangChain + 百炼）时作为**输入输出与事件字段**的约定依据，与 [需求规格说明书.md](./需求规格说明书.md) 中的 FR-LM、FR-SQL、FR-API 对齐。

**联调实测参考脚本**：[backend/scripts/test_qwen_stream_tools.py](../backend/scripts/test_qwen_stream_tools.py)（`qwen3-max` + DashScope OpenAI 兼容网关）。

---

## 1. 运行与配置约定

| 配置项 | 环境变量（建议） | 说明 |
|--------|------------------|------|
| API Key | `DASHSCOPE_API_KEY` 或 `OPENAI_API_KEY` | 百炼 / DashScope 的 `sk-` Key，**仅服务端**，禁止写入前端仓库 |
| 兼容网关 | `DASHSCOPE_COMPAT_BASE`（可选） | 默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 模型名 | `QWEN_MODEL`（可选） | 默认 `qwen3-max`；变更时需回归流式与工具调用 |

LangChain 侧使用 **`langchain_openai.ChatOpenAI`**，传入 `model`、`api_key`、`base_url`，与官方「OpenAI 兼容端点」用法一致。

---

## 2. 非流式对话（`invoke`）— 返回结构

对 `HumanMessage` / `SystemMessage` 列表执行 `llm.invoke(messages)` 时，结果为 **`langchain_core.messages.ai.AIMessage`**。Phase 2 业务代码应**优先**使用下列字段，并在对外 API 中**规范化**为统一 JSON（见第 5 节）。

### 2.1 纯文本回复

| 字段 | 类型 | 说明 |
|------|------|------|
| `content` | `str` | 助手自然语言正文；可能为空（例如仅工具调用时） |
| `response_metadata` | `dict` | 常含 `model_name`（如 `qwen3-max`）、`finish_reason`（如 `stop`）、`token_usage` 等 |
| `additional_kwargs` | `dict` | 厂商原始载荷，**不要**作为对前端唯一来源，仅排障或透传可选 |

### 2.2 函数 / 工具调用（`bind_tools` 后）

当模型选择调用工具时，典型情况为 **`content` 为空或极短**，有效负载在工具相关字段中。

**LangChain 已解析字段（业务逻辑优先读此结构）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `tool_calls` | `list[dict]` | 每个元素为**字典**，标准键见下表 |

`tool_calls[]` 单条字典约定：

| 键 | 类型 | 必填 | 说明 |
|----|------|------|------|
| `name` | `str` | 是 | 工具函数名 |
| `args` | `dict` | 是 | **已解析为对象**的参数（如 `{"city": "上海", "unit": "celsius"}`） |
| `id` | `str` | 是 | 调用 ID，形如 `call_xxxxxxxx`，用于多轮工具结果回传 |
| `type` | `str` | 是 | LangChain 侧常见为 `"tool_call"` |

**厂商原始形态（`additional_kwargs`，辅助对照）：**

- `additional_kwargs["tool_calls"]`：OpenAI 风格列表；元素含 `id`、`type`（如 `"function"`）、`function.name`、`function.arguments`（**JSON 字符串**，需 `json.loads` 才能得到与 `tool_calls[].args` 等价对象）。

**实现要求：**

- 执行业务工具时，以 **`AIMessage.tool_calls`** 的 `name` + `args` 为准。  
- 若某版本/场景下 `tool_calls` 为空但 `additional_kwargs["tool_calls"]` 有值，应实现**兜底解析**（解析 `function.arguments` 字符串），并记录日志。

---

## 3. 流式对话（`stream` / SSE）— Chunk 字段

对同一 `ChatOpenAI` 使用 `streaming=True` 时，`llm.stream(messages)` 产出 **`AIMessageChunk`**。

### 3.1 纯文本流式

| 字段 | 说明 |
|------|------|
| `content` | 增量文本片段；前端/网关需**拼接**成完整回复 |
| `tool_call_chunks` | 纯文本场景下通常存在但可为空列表或占位 |
| `response_metadata` | **末包或关键包**可能出现 `finish_reason`（`stop`）、`model_name` |

### 3.2 工具调用流式（`bind_tools` + `stream`）

| 字段 | 说明 |
|------|------|
| `tool_call_chunks` | **增量**描述工具调用；元素常含 `name`、`args`（**字符串片段**）、`id`、`index`、`type`（如 `tool_call_chunk`） |
| `tool_calls` | 流式过程中可能为**部分合并**的中间态，`args` **不一定**已是完整 `dict` |
| `additional_kwargs["tool_calls"]` | 同样可能分段出现在 `function.arguments` 中 |

**强制规范（Phase 2 实现 SSE 或流式接口时）：**

1. **不得**假设某一中间 chunk 的 `tool_calls[].args` 已是完整 JSON 对象。  
2. 工具调用场景应：  
   - **要么**在服务端对流结束后用 LangChain/厂商合并结果，再对外发**一条**「工具调用就绪」事件；  
   - **要么**在网关内对 `tool_call_chunks` 按 `index`/`id` **拼接 `args` 字符串**后 `json.loads`，再下发统一结构。  
3. 对外事件模型（见第 5 节）中，工具调用应使用**与 `invoke` 相同的** `name`、`args`（对象）、`id` 字段，避免混用字符串与对象。

---

## 4. `finish_reason` 与分支逻辑

| `finish_reason`（常见于 `response_metadata`） | 含义 | 后端处理建议 |
|-----------------------------------------------|------|----------------|
| `stop` | 自然结束（多为纯文本） | 输出最终 `content` |
| `tool_calls` | 需执行工具 | 解析 `tool_calls`（或兜底 `additional_kwargs`），执行工具后再发起下一轮模型调用 |
| 其他 | 以 DashScope/OpenAI 兼容文档为准 | 记录原始 metadata，返回可理解的业务错误码或降级文案 |

---

## 5. 对外 API 规范化模型（推荐）

Phase 2 暴露给前端的响应（含 SSE 的 data JSON）**不应**直接暴露原始 `AIMessageChunk` 全量字段，建议统一为：

### 5.1 非流式一次返回（示例）

```json
{
  "reply": "string，自然语言，可为空",
  "tool_calls": [
    {
      "id": "call_xxx",
      "name": "tool_name",
      "args": {}
    }
  ],
  "sql": "string，可选，NL2SQL 场景",
  "data": {
    "columns": ["string"],
    "rows": [["..."]]
  },
  "meta": {
    "model": "qwen3-max",
    "finish_reason": "stop"
  }
}
```

- `tool_calls`：无工具调用时为 `[]`。  
- `args`：**始终为 JSON 对象**（由服务端保证解析完成）。

### 5.2 流式 SSE 事件类型（示例）

| 事件类型 | payload 要点 |
|----------|----------------|
| `token` 或 `delta` | `{ "text": "增量文本" }` |
| `tool_calls_ready` | `{ "tool_calls": [ { "id", "name", "args" } ] }`（仅在与模型对齐且 **args 已完整解析** 后发送） |
| `final` | `{ "reply", "sql", "data", "meta" }` 与 5.1 对齐，表示本轮对用户可见结果已确定 |
| `error` | `{ "code", "message" }`，不暴露密钥与堆栈 |

---

## 6. NL2SQL 与工具调用的关系

- 若采用 **Agent / 多步工具**，中间轮次的 `tool_calls` 可能多次出现；**对前端**可只暴露最终轮的 `reply` + `sql` + `data`，或按产品需要增加 `steps`（可选）。  
- 执行 SQL 前必须通过安全策略（只读、单语句、超时、行数上限），与需求文档 FR-SQL 一致。

---

## 7. LangChain 官方 NL2SQL 相关组件（经 LangChain MCP 文档检索）

官方文档明确提供**面向 SQL 库的自然语言问答**路径，与本项目 SQLite + NL2SQL 需求一致。以下为摘要与入口链接（Python 为主）。

### 7.1 推荐主路径：SQL Agent（高层抽象）

- **文档**：[Build a SQL agent (Python)](https://docs.langchain.com/oss/python/langchain/sql-agent)  
- **依赖（文档示例）**：`langchain`、`langgraph`、`langchain-community`；LLM 需支持 **tool-calling**（本项目可用已验证的 `ChatOpenAI` + 百炼兼容端 + `qwen3-max`）。  
- **数据库封装**：`langchain_community.utilities.SQLDatabase`  
  - 示例：`SQLDatabase.from_uri("sqlite:///Chinook.db")`  
  - 提供方言、表名、`run(sql)` 等能力。  
- **工具包**：`langchain_community.agent_toolkits.SQLDatabaseToolkit`  
  - `toolkit = SQLDatabaseToolkit(db=db, llm=model)`，`tools = toolkit.get_tools()`。  
- **内置工具（典型名称）**：  
  - `sql_db_list_tables`：列出表  
  - `sql_db_schema`：按表拉 schema 与样例行  
  - `sql_db_query_checker`：执行前用 LLM 复查 SQL  
  - `sql_db_query`：执行查询并返回结果（**生产环境必须配合权限收窄 + 服务端再校验**，见需求 FR-SQL）。  
- **编排**：`langchain.agents.create_agent(model, tools, system_prompt=...)`，对 `agent.stream(..., stream_mode="values")` 观察多步工具调用与最终回答。

### 7.2 进阶：LangGraph 自定义 SQL Agent

- **文档**：[Build a custom SQL agent (LangGraph)](https://docs.langchain.com/oss/python/langgraph/sql-agent)  
- 在预置 Agent 行为不足时（例如强制节点顺序、更严的 SQL 审核），用 LangGraph 自建状态机；文档说明可与高层 SQL Agent 教程对照阅读。

### 7.3 大型库 / 多业务域：按需加载 Schema（Skills 模式）

- **文档**：[Build a SQL assistant with on-demand skills (Python)](https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant)  
- 通过 **progressive disclosure**，仅在需要时经 tool 加载某垂直领域的完整 schema/业务说明，避免一次性塞满上下文；适合「表很多」的场景。完整执行链路仍可参考 **7.1 SQL Agent**。

### 7.4 与人机协同（可选）

- 同一 SQL Agent 文档后半部分：`HumanInTheLoopMiddleware` + `interrupt_on={"sql_db_query": True}`，可在执行 `sql_db_query` 前暂停等待人工确认（适合内网高敏库）。

### 7.5 与本项目 Phase 2 的对应关系

| 能力 | LangChain 侧 |
|------|----------------|
| 自然语言 → SQL → 执行 → 解释 | `SQLDatabase` + `SQLDatabaseToolkit` + `create_agent` |
| 流式 / SSE | Agent `stream` + 按本文 **第 3 节** 规范映射为对外事件 |
| 只读与安全 | 除文档中的 DML 禁止提示外，须在应用层做 SQL 白名单/单语句/超时等（需求文档 FR-SQL） |

### 7.6 实测：`qwen3-max` + `create_agent` + `SQLDatabaseToolkit` 的入参 / 出参（本仓库脚本）

**复现脚本**：[backend/scripts/test_nl2sql_qwen_output.py](../backend/scripts/test_nl2sql_qwen_output.py)（临时 SQLite + 与 `test_qwen_stream_tools.py` 相同的百炼兼容 `ChatOpenAI`）。

**Agent 入参（`invoke` / `stream` 共用）**

```json
{
  "messages": [
    { "role": "user", "content": "用户自然语言问题" }
  ]
}
```

**Agent 出参（`invoke` 返回值顶层）**

| 键 | 类型 | 说明 |
|----|------|------|
| `messages` | `list[BaseMessage]` | 完整对话轨迹；**无其它顶层键**（以当前 LangChain 1.x `create_agent` 为准） |

**`messages` 中交替出现的类型**

| `class` | 主要字段 | 说明 |
|---------|-----------|------|
| `HumanMessage` | `content` | 用户输入 |
| `AIMessage` | `content`，可选 `tool_calls`，`additional_kwargs` | 无工具时 `content` 为最终自然语言；有工具时常见 `content==""` 且 `tool_calls` 非空 |
| `ToolMessage` | `content`，`name`，`tool_call_id` | 工具文本结果；`name` 与对应 `AIMessage.tool_calls[].name` 一致 |

**`AIMessage.tool_calls[]` 单条结构（与 Phase2 第 2.2 节一致）**

| 键 | 说明 |
|----|------|
| `name` | 工具名，见下表 |
| `args` | **dict**，见下表（键名以本环境实测为准，勿写死为仅 `query`） |
| `id` | 与 `ToolMessage.tool_call_id` 对应 |
| `type` | 实测为 `"tool_call"` |

**`SQLDatabaseToolkit` 各工具在 `tool_calls[].args` 中的键名（实测）**

| `name` | `args` 键 | 示例值 |
|--------|-----------|--------|
| `sql_db_list_tables` | `tool_input` | `""`（空字符串） |
| `sql_db_schema` | `table_names` | `"sales"` 或 `"table1, table2"` |
| `sql_db_query_checker` | `query` | SQL 字符串 |
| `sql_db_query` | `query` | SQL 字符串 |

**FastAPI 映射建议**

- 请求体：接收用户 `content`，组装为 `{"messages": [{"role":"user","content": ...}]}`。  
- 响应体：从 `result["messages"]` 取**最后一条带非空 `content` 的 `AIMessage`** 作为 `reply`；从**名为 `sql_db_query` 的 `tool_calls`** 提取 `args["query"]` 作为 `sql`；将对应 `ToolMessage.content` 解析为表格的 `columns`/`rows`（当前为 Python 字面量字符串，需安全解析或改执行层直接返回结构化结果）。

---

## 8. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-04-04 | 基于 `qwen3-max` + LangChain `ChatOpenAI` 实测整理流式与 `tool_calls` 字段规范 |
| 1.1 | 2026-04-04 | 经 LangChain MCP 检索补充官方 NL2SQL（SQL Agent / SQLDatabase / Toolkit）组件说明与文档链接 |
| 1.2 | 2026-04-04 | 补充 `create_agent`+`SQLDatabaseToolkit` 在 `qwen3-max` 下实测的入参/出参及 `tool_calls.args` 键名 |

---

*实现 Phase 2 时，若百炼 API 或 LangChain 版本升级导致字段变化，应更新本页并重新跑 [test_qwen_stream_tools.py](../backend/scripts/test_qwen_stream_tools.py)、[test_nl2sql_qwen_output.py](../backend/scripts/test_nl2sql_qwen_output.py) 做回归。*
