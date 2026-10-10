from langchain.agents import create_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.nl2sql.safe_database import SafeSQLDatabase


def build_chat_model() -> ChatOpenAI:
    s = get_settings()
    key = s.llm_api_key()
    if not key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY，无法调用大模型。")
    return ChatOpenAI(
        model=s.qwen_model,
        api_key=key,
        base_url=s.dashscope_compat_base,
        temperature=0.1,
    )


def build_sql_agent():
    """创建带 SQLDatabaseToolkit 的 Agent（每次请求新建，避免状态串话）。"""
    settings = get_settings()
    model = build_chat_model()
    db = SafeSQLDatabase.from_uri(
        settings.analytics_db_url,
        engine_args={
            "connect_args": {
                "check_same_thread": False,
                "timeout": settings.sql_statement_timeout_sec,
            }
        },
    )
    toolkit = SQLDatabaseToolkit(db=db, llm=model)
    tools = toolkit.get_tools()

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
        top_k=settings.nl2sql_top_k,
    )
    return create_agent(model, tools, system_prompt=system_prompt)
