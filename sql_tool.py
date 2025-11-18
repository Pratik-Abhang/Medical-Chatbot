from langchain.tools import tool
from sqlalchemy import text
from db import get_mysql_engine

engine = get_mysql_engine()

@tool("sql_query", return_direct=False)
def sql_query(query: str) -> str:
    """Run a SQL SELECT query on the Medical database."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            return str(rows)
    except Exception as e:
        return f"SQL Error: {str(e)}"


@tool("sql_execute", return_direct=False)
def sql_execute(query: str) -> str:
    """Run SQL INSERT/UPDATE commands on the Medical database."""
    try:
        with engine.begin() as conn:
            conn.execute(text(query))
            return "Query executed successfully."
    except Exception as e:
        return f"Execution Error: {str(e)}"
