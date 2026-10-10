"""NL2SQL 执行前 SQL 白名单（单条 SELECT / WITH…SELECT）。"""

import re


def is_safe_select_sql(sql: str) -> bool:
    if not sql or not isinstance(sql, str):
        return False
    s = sql.strip()
    if not s:
        return False
    core = s.rstrip(";").strip()
    if not core:
        return False
    # 禁止多语句（简单判定）
    if core.count(";") > 0:
        return False
    upper = core.upper()
    blocked = (
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "DROP ",
        "ALTER ",
        "CREATE ",
        "ATTACH ",
        "DETACH ",
        "PRAGMA ",
        "REPLACE ",
    )
    for b in blocked:
        if b in upper:
            return False
    if upper.startswith("SELECT") or upper.startswith("WITH"):
        return True
    return False


def truncate_rows_notice(sql: str, max_rows: int) -> str:
    """若未带 LIMIT，可在应用层追加（此处返回提示用 SQL，由调用方决定是否改写）。"""
    if re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        return sql
    return f"{sql.rstrip(';').strip()} LIMIT {max_rows}"
