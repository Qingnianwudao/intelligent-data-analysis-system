"""
NL2SQL 组件 + 已验证的 Qwen3（百炼 OpenAI 兼容）联调：打印真实「入参 / 出参」形态。

目的：确定 create_agent + SQLDatabaseToolkit 在实际调用中的：
  - agent.invoke / agent.stream 的状态字典结构
  - 各步 Message 类型与 tool_calls / ToolMessage 字段
  - sql_db_* 工具在 tool_calls[].args 中的参数名（如 query）

依赖（与 LangChain 官方 SQL Agent 教程一致，需 LangChain 1.x）：
  pip install langchain langchain-core langchain-openai langchain-community langgraph

运行（PowerShell）:
  cd backend
  .\\.venv\\Scripts\\activate
  $env:DASHSCOPE_API_KEY="YOUR_DASHSCOPE_API_KEY"
  $env:QWEN_MODEL="qwen3-max"   # 可选
  python scripts/test_nl2sql_qwen_output.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langchain.agents import create_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

DASHSCOPE_COMPAT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-max"


def _require_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        print(
            "请设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY 后重试。",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def build_qwen_chat() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("QWEN_MODEL", DEFAULT_MODEL),
        api_key=_require_key(),
        base_url=os.environ.get("DASHSCOPE_COMPAT_BASE", DASHSCOPE_COMPAT_BASE),
        temperature=0.1,
    )


def create_demo_sqlite() -> Path:
    """最小业务库：月份销售额，便于一条聚合 SQL 即可回答。"""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="nl2sql_demo_")
    os.close(fd)
    p = Path(path)
    conn = sqlite3.connect(p)
    try:
        conn.executescript(
            """
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                amount REAL NOT NULL
            );
            INSERT INTO sales (month, amount) VALUES
                ('2024-01', 120.5),
                ('2024-02', 200.0),
                ('2024-03', 95.0),
                ('2024-04', 200.0);
            """
        )
        conn.commit()
    finally:
        conn.close()
    return p


def serialize_message(m: BaseMessage) -> dict[str, Any]:
    """将单条消息转为可 JSON 打印的结构（便于对接 FastAPI 响应模型）。"""
    out: dict[str, Any] = {"class": m.__class__.__name__}
    content = getattr(m, "content", None)
    if content is not None:
        out["content"] = content
    tc = getattr(m, "tool_calls", None)
    if tc:
        out["tool_calls"] = list(tc)
    name = getattr(m, "name", None)
    if name:
        out["name"] = name
    tcid = getattr(m, "tool_call_id", None)
    if tcid:
        out["tool_call_id"] = tcid
    ak = getattr(m, "additional_kwargs", None) or {}
    if ak:
        out["additional_kwargs"] = dict(ak)
    return out


def build_sql_agent(db: SQLDatabase, model: ChatOpenAI):
    toolkit = SQLDatabaseToolkit(db=db, llm=model)
    tools = toolkit.get_tools()
    print("\n=== Toolkit 工具列表（名称即模型 tool_calls[].name） ===")
    for t in tools:
        print(f"  - {t.name}")

    system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results and return a concise answer in Chinese.
Unless the user specifies otherwise, limit results to at most {top_k} rows.
You MUST use sql_db_query_checker before sql_db_query when available.
DO NOT execute INSERT, UPDATE, DELETE, DROP or any DML other than SELECT.
Start by listing tables if needed, then inspect relevant schemas.
""".format(
        dialect=db.dialect,
        top_k=10,
    )
    return create_agent(model, tools, system_prompt=system_prompt)


def print_json(title: str, obj: Any) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}")
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    model = build_qwen_chat()
    db_path = create_demo_sqlite()
    try:
        uri = f"sqlite:///{db_path.as_posix()}"
        print(f"临时 SQLite: {db_path}")
        db = SQLDatabase.from_uri(uri)
        print(f"dialect={db.dialect} tables={db.get_usable_table_names()}")

        agent = build_sql_agent(db, model)
        question = "哪个月销售额最高？金额是多少？只回答结论。"

        # ---------- 1) invoke 最终状态（推荐作为「同步接口」参考） ----------
        print("\n>>> 调用 agent.invoke 入参模板 <<<")
        invoke_input = {"messages": [{"role": "user", "content": question}]}
        print_json("invoke 请求体（实际传给 agent 的 dict）", invoke_input)

        result = agent.invoke(invoke_input)

        print("\n>>> agent.invoke 返回值的顶层 keys <<<")
        print(list(result.keys()))

        messages_out = [serialize_message(m) for m in result["messages"]]
        print_json("invoke 返回 messages 序列化（对接 API 时可只取最后一条 AIMessage）", messages_out)

        # ---------- 2) stream stream_mode=values（逐步状态，用于 SSE 设计） ----------
        print("\n>>> agent.stream(..., stream_mode='values') 每步 messages 条数 <<<")
        step_index = 0
        last_step: dict[str, Any] | None = None
        for step in agent.stream(invoke_input, stream_mode="values"):
            last_step = step
            n = len(step.get("messages", []))
            last_cls = type(step["messages"][-1]).__name__ if n else None
            print(f"  step[{step_index}] messages={n} last={last_cls}")
            step_index += 1

        if last_step and "messages" in last_step:
            last_step_messages = [serialize_message(m) for m in last_step["messages"]]
            print_json("最后一帧完整 messages（流式结束态应与 invoke 一致）", last_step_messages)
        else:
            print("(stream 无数据，跳过最后一帧打印)")

        # ---------- 3) 接口摘要（给 OpenAPI / 前端用的字段建议） ----------
        summary = {
            "agent_input_shape": {
                "messages": [
                    {"role": "user|system|assistant|...", "content": "string"},
                ],
            },
            "agent_output_shape": {
                "top_level_keys": list(result.keys()),
                "messages_item_classes": [type(m).__name__ for m in result["messages"]],
            },
            "tool_call_args_observed": _collect_tool_arg_keys(messages_out),
            "assistant_final_text": _last_ai_text(result["messages"]),
        }
        print_json("NL2SQL Agent 实际接口摘要（本机一次运行归纳）", summary)

    finally:
        try:
            db_path.unlink(missing_ok=True)
        except OSError:
            pass


def _collect_tool_arg_keys(serialized: list[dict[str, Any]]) -> dict[str, list[str]]:
    """从序列化后的消息里收集各 tool 的 args 键名。"""
    found: dict[str, set[str]] = {}
    for item in serialized:
        for tc in item.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            name = tc.get("name") or ""
            args = tc.get("args") or {}
            if isinstance(args, dict):
                found.setdefault(name, set()).update(args.keys())
    return {k: sorted(v) for k, v in found.items()}


def _last_ai_text(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and (m.content or "").strip():
            return str(m.content)
    return ""


if __name__ == "__main__":
    main()
