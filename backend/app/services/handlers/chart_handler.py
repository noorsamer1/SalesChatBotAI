from app.core.db import engine
from sqlalchemy import text

def handle_chart(response):
    try:
        # Extract required fields
        sql = response.get("code", "").strip()
        x_column = response.get("x")
        y_column = response.get("y")
        chart_title = response.get("title", "")
        chart_kind = response.get("kind", "bar")

        if not (sql and x_column and y_column):
            raise ValueError("Missing 'code', 'x', or 'y' in chart response")

        # Execute the SQL safely
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())  # Convert RMKeyView to list
            normalized_cols = [col.lower() for col in columns]

        # Match column names case-insensitively
        if x_column.lower() not in normalized_cols or y_column.lower() not in normalized_cols:
            raise ValueError(f"'{x_column}' or '{y_column}' not in SQL result columns: {columns}")

        # Map back to actual index
        x_index = normalized_cols.index(x_column.lower())
        y_index = normalized_cols.index(y_column.lower())

        # Extract chart data
        labels = [row[x_index] for row in rows]
        values = [row[y_index] for row in rows]

        # Return frontend-friendly format
        return {
            "type": "chart",
            "title": chart_title,
            "chart_data": {
                "x_axis": x_column,
                "y_axis": y_column,
                "labels": labels,
                "values": values
            },
            "kind": chart_kind
        }

    except Exception as e:
        print(f"[chart_handler.py] Chart generation failed: {e}")  # Optional for dev logs
        return {
            "type": "text",
            "text": f"⚠️ Chart generation failed: {str(e)}"
        }
