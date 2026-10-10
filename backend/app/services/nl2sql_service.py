import json
from collections.abc import Iterator
from typing import Any

from app.nl2sql.agent_factory import build_sql_agent
from app.nl2sql.extract import extract_from_agent_messages


def _invoke_payload(
    history_pairs: list[tuple[str, str]],
    user_message: str,
) -> dict[str, Any]:
    msgs: list[dict[str, str]] = []
    for role, text in history_pairs:
        r = "user" if role == "user" else "assistant"
        msgs.append({"role": r, "content": text})
    msgs.append({"role": "user", "content": user_message})
    return {"messages": msgs}


def run_nl2sql_turn(
    history_pairs: list[tuple[str, str]],
    user_message: str,
) -> dict[str, Any]:
    agent = build_sql_agent()
    result = agent.invoke(_invoke_payload(history_pairs, user_message))
    raw_messages = result["messages"]
    pack = extract_from_agent_messages(raw_messages)
    pack["meta"] = {
        **(pack.get("meta") or {}),
        "message_count": len(raw_messages),
    }
    return pack


def stream_nl2sql_sse(
    history_pairs: list[tuple[str, str]],
    user_message: str,
) -> Iterator[str]:
    """SSE：step 事件 + 最终 final 事件（与同步接口同一 JSON 形状）。"""
    agent = build_sql_agent()
    payload = _invoke_payload(history_pairs, user_message)
    last_step: dict[str, Any] | None = None
    for i, step in enumerate(agent.stream(payload, stream_mode="values")):
        last_step = step
        msgs = step.get("messages") or []
        last = msgs[-1] if msgs else None
        chunk = {
            "step": i,
            "message_count": len(msgs),
            "last_type": type(last).__name__ if last else None,
        }
        yield f"event: step\ndata: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    if last_step and "messages" in last_step:
        pack = extract_from_agent_messages(last_step["messages"])
        pack["meta"] = {
            **(pack.get("meta") or {}),
            "message_count": len(last_step["messages"]),
        }
        yield f"event: final\ndata: {json.dumps(pack, ensure_ascii=False, default=str)}\n\n"
