"""
阿里云百炼 / DashScope：Qwen OpenAI 兼容模式 + LangChain ChatOpenAI 联调脚本。

观察项：
1. 流式输出：每个 chunk 的 content / tool_call_chunks 等字段
2. 函数调用：非流式 invoke 后 AIMessage.tool_calls 的结构（name、args、id、type）

勿将 API Key 写入仓库。运行前设置环境变量（PowerShell 示例）：
  $env:DASHSCOPE_API_KEY="YOUR_DASHSCOPE_API_KEY"
  python scripts/test_qwen_stream_tools.py

或在 backend 目录下：
  python -m scripts.test_qwen_stream_tools
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# Windows 终端默认编码易导致中文乱码
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# 百炼 OpenAI 兼容网关（LangChain 文档：可用 ChatOpenAI + 自定义 base_url）
DASHSCOPE_COMPAT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-max"


def _require_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        print(
            "错误：请设置环境变量 DASHSCOPE_API_KEY 或 OPENAI_API_KEY（DashScope 的 sk- key）。",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _print_chunk(i: int, chunk: Any) -> None:
    """打印流式 chunk 的关键字段，便于对照厂商实际返回。"""
    parts: list[str] = [f"--- chunk[{i}] type={type(chunk).__name__} ---"]
    if getattr(chunk, "content", None):
        parts.append(f"  content: {chunk.content!r}")
    if getattr(chunk, "tool_call_chunks", None):
        parts.append(f"  tool_call_chunks: {chunk.tool_call_chunks!r}")
    if getattr(chunk, "tool_calls", None):
        parts.append(f"  tool_calls: {chunk.tool_calls!r}")
    if getattr(chunk, "response_metadata", None):
        parts.append(f"  response_metadata: {chunk.response_metadata!r}")
    if getattr(chunk, "additional_kwargs", None):
        parts.append(f"  additional_kwargs: {chunk.additional_kwargs!r}")
    # 避免漏掉其它属性
    if hasattr(chunk, "model_fields_set") and chunk.model_fields_set:
        parts.append(f"  model_fields_set: {chunk.model_fields_set}")
    print("\n".join(parts))


def build_llm(*, streaming: bool) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("QWEN_MODEL", DEFAULT_MODEL),
        api_key=_require_key(),
        base_url=os.environ.get("DASHSCOPE_COMPAT_BASE", DASHSCOPE_COMPAT_BASE),
        streaming=streaming,
        temperature=0.2,
    )


def run_stream_plain() -> None:
    print("\n========== 1) 纯文本流式（无工具） ==========\n")
    llm = build_llm(streaming=True)
    messages = [
        SystemMessage(content="你是简洁助手，用中文回答。"),
        HumanMessage(content="用不超过30字介绍什么是 NL2SQL。"),
    ]
    full = ""
    for i, chunk in enumerate(llm.stream(messages)):
        _print_chunk(i, chunk)
        if chunk.content:
            full += str(chunk.content)
    print(f"\n[拼接后的文本]\n{full}\n")


@tool
def query_city_temperature(city: str, unit: str = "celsius") -> str:
    """根据城市名查询气温（演示用假数据）。

    Args:
        city: 城市中文名，如 北京
        unit: 温度单位，celsius 或 fahrenheit
    """
    return json.dumps(
        {"city": city, "unit": unit, "temp": 22, "condition": "晴"},
        ensure_ascii=False,
    )


def run_invoke_tools() -> None:
    print("\n========== 2) 非流式 + 工具绑定（观察 tool_calls 字段） ==========\n")
    llm = build_llm(streaming=False).bind_tools([query_city_temperature])
    messages = [
        HumanMessage(content="查一下上海的气温，用摄氏度。"),
    ]
    ai: AIMessage = llm.invoke(messages)
    print(f"type(ai): {type(ai)}")
    print(f"content: {ai.content!r}")
    print(f"tool_calls (原始): {ai.tool_calls!r}")
    if ai.tool_calls:
        for j, tc in enumerate(ai.tool_calls):
            print(f"\n  tool_calls[{j}] type={type(tc).__name__}")
            if isinstance(tc, dict):
                print(f"    keys: {list(tc.keys())}")
                for k, v in tc.items():
                    print(f"    {k}: {v!r}")
            else:
                print(f"    repr: {tc!r}")
    print(f"\nadditional_kwargs: {ai.additional_kwargs!r}")
    print(f"response_metadata: {ai.response_metadata!r}")


def run_stream_tools() -> None:
    print("\n========== 3) 流式 + 工具绑定（观察 tool_call_chunks） ==========\n")
    llm = build_llm(streaming=True).bind_tools([query_city_temperature])
    messages = [HumanMessage(content="查一下深圳气温，摄氏度。")]
    acc_text = ""
    for i, chunk in enumerate(llm.stream(messages)):
        _print_chunk(i, chunk)
        if chunk.content:
            acc_text += str(chunk.content)
    print(f"\n[流式文本拼接]\n{acc_text}\n")


def main() -> None:
    print(f"model={os.environ.get('QWEN_MODEL', DEFAULT_MODEL)}")
    print(f"base_url={os.environ.get('DASHSCOPE_COMPAT_BASE', DASHSCOPE_COMPAT_BASE)}")
    run_stream_plain()
    run_invoke_tools()
    run_stream_tools()
    print("\n全部完成。")


if __name__ == "__main__":
    main()
