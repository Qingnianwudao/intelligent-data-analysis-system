from typing import Any, Literal, Optional, Sequence, Union

from langchain_community.utilities import SQLDatabase
from sqlalchemy.exc import OperationalError, TimeoutError as SATimeoutError

from app.config import get_settings
from app.nl2sql.sql_safety import is_safe_select_sql, truncate_rows_notice


class SafeSQLDatabase(SQLDatabase):
    """在 LangChain SQLDatabase.run 前做只读校验，并限制返回行数（追加 LIMIT）。"""

    def run(
        self,
        command: Union[str, Any],
        fetch: Literal["all", "one", "cursor"] = "all",
        include_columns: bool = False,
        *,
        parameters: Optional[dict[str, Any]] = None,
        execution_options: Optional[dict[str, Any]] = None,
    ) -> Union[str, Sequence[dict[str, Any]], Any]:
        settings = get_settings()
        if isinstance(command, str):
            if not is_safe_select_sql(command):
                return "Error: only a single SELECT or WITH…SELECT query is allowed."
            command = truncate_rows_notice(command, settings.nl2sql_max_rows)
        try:
            return super().run(
                command,
                fetch,
                include_columns,
                parameters=parameters,
                execution_options=execution_options,
            )
        except (OperationalError, SATimeoutError) as e:
            return f"Error: {e!s}"
