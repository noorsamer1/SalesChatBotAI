from app.core.db import engine
from sqlalchemy import text

# Example of a "table" response:
# {
#   "type": "table",
#   "title": "Top 5 customers by profit",
#   "code": "SELECT customer_name_e, SUM(sales_prof) AS total_profit FROM orders GROUP BY customer_name_e ORDER BY total_profit DESC LIMIT 5"
# }

########################################
# ⚠️ Frontend connect needed ⚠️
########################################

def handle_table(response):
    sql = response.get("code", "").strip()
    columns = []
    rows = []

    if sql:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                columns = list(result.keys())  # Column names

        except Exception as e:
            return {
                "type": "text",
                "text": f"[DB ERROR: {e}]"
            }

    # Convert rows from tuples to lists (for JSON safety)
    rows = [list(row) for row in rows]

    return {
        "type": "table",
        "title": response.get("title", "Table"),
        "columns": columns,
        "rows": rows
    }
