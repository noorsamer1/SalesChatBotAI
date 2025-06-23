from app.core.db import engine
from sqlalchemy import text

DEFAULT_LIMIT = 25  # Pagination threshold

def handle_table(response):
    try:
        sql = response.get("code", "").strip()
        table_title = response.get("title", "Table")

        if not sql:
            raise ValueError("Missing 'code' in table response")

        # Execute the SQL
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            # Convert SQLAlchemy keys to list of strings
            columns = [str(col) for col in result.keys()]

        total_rows = len(rows)

        if total_rows > DEFAULT_LIMIT:
            # Paginate
            paginated_rows = rows[:DEFAULT_LIMIT]
            return {
                "type": "table",
                "title": table_title,
                "table_data": {  # Match frontend expectation
                    "columns": columns,
                    "rows": [list(row) for row in paginated_rows],
                    "paginated": True,
                    "page": 1,
                    "total_pages": (total_rows + DEFAULT_LIMIT - 1) // DEFAULT_LIMIT,
                    "total_rows": total_rows
                }
            }
        else:
            # Return full table
            return {
                "type": "table",
                "title": table_title,
                "table_data": {  # Match frontend expectation
                    "columns": columns,
                    "rows": [list(row) for row in rows],
                    "paginated": False
                }
            }

    except Exception as e:
        print(f"[table_handler.py] Table generation failed: {e}")
        return {
            "type": "text",
            "text": f"⚠️ Table generation failed: {str(e)}"
        }