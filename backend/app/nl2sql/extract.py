"""从 Agent 返回的 messages 中提取 reply / sql / 表格数据（与 Phase2 规范一致）。"""

import ast
import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage


def parse_tool_tabular_content(content: str) -> tuple[list[str], list[list[Any]]]:
    """将 sql_db_query 的 ToolMessage.content（常为 Python 字面量）解析为 columns + rows。"""
    if not content or not str(content).strip():
        return [], []
    try:
        data = ast.literal_eval(content.strip())
    except (SyntaxError, ValueError, TypeError):
        return [], []
    if not isinstance(data, list) or len(data) == 0:
        return [], []
    first = data[0]
    if isinstance(first, dict):
        cols = list(first.keys())
        rows = [list(r.values()) for r in data if isinstance(r, dict)]
        return cols, rows
    if isinstance(first, (list, tuple)):
        width = len(first)
        cols = [f"c{i}" for i in range(width)]
        rows = [list(r) if isinstance(r, (list, tuple)) else [r] for r in data]
        return cols, rows
    return [], []


def extract_from_agent_messages(messages: list[BaseMessage]) -> dict[str, Any]:
    """提取最终回复文本、最后一条 sql_db_query 的 SQL 与结果。"""
    reply = ""
    sql_used: str | None = None
    query_raw: str | None = None
    model_name: str | None = None

    for m in messages:
        if isinstance(m, AIMessage):
            if m.content and str(m.content).strip():
                reply = str(m.content)
            meta = getattr(m, "response_metadata", None) or {}
            model_name = meta.get("model_name") or model_name

    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.tool_calls:
            for tc in m.tool_calls:
                if not isinstance(tc, dict):
                    continue
                if tc.get("name") == "sql_db_query":
                    args = tc.get("args") or {}
                    if isinstance(args, dict):
                        sql_used = args.get("query")
                    break
            if sql_used:
                break

    for m in reversed(messages):
        if isinstance(m, ToolMessage) and m.name == "sql_db_query":
            query_raw = str(m.content)
            break

    columns, rows = parse_tool_tabular_content(query_raw or "")

    return {
        "reply": reply,
        "sql": sql_used,
        "data": {"columns": columns, "rows": rows},
        "meta": {"model": model_name},
    }


def messages_to_jsonable(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        item: dict[str, Any] = {"class": m.__class__.__name__}
        if getattr(m, "content", None) is not None:
            item["content"] = m.content
        tc = getattr(m, "tool_calls", None)
        if tc:
            item["tool_calls"] = list(tc)
        if getattr(m, "name", None):
            item["name"] = m.name
        if getattr(m, "tool_call_id", None):
            item["tool_call_id"] = m.tool_call_id
        out.append(item)
    return out
