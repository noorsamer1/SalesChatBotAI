<<<<<<< HEAD
from app.core.db import engine
from sqlalchemy import text

# Example of a "chart" response (bar):
# {
#   "type": "chart",
#   "title": "Sales by division",
#   "code": "SELECT division_name, SUM(sales_value) AS total_sales FROM orders GROUP BY division_name",
#   "x": "division_name",
#   "y": "total_sales",
#   "kind": "bar"
# }
=======
from .handlersCommnFunction import *

def execute_query_with_timeout(sql: str, timeout: int = 30) -> tuple[list, list]:
    """Execute SQL query with cross-platform timeout"""
    def run_query():
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
            return rows, columns
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_query)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Query execution timed out after {timeout} seconds")
>>>>>>> master

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

<<<<<<< HEAD
        # Execute the SQL safely
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())  # Convert RMKeyView to list
            normalized_cols = [col.lower() for col in columns]
=======
        try:
            # Execute the SQL safely with timeout
            rows, columns = execute_query_with_timeout(sql, timeout=30)
            normalized_cols = [col.lower() for col in columns]
        except TimeoutError:
            logger.error("Chart query timed out")
            return {
                "type": "text", 
                "text": "⚠️ Query took too long to execute. Please try a more specific question."
            }
        except Exception as e:
            logger.error(f"Chart query error: {e}")
            return {
                "type": "text",
                "text": f"⚠️ Database error: {str(e)}"
            }

        # Validate data size (prevent memory issues)
        if len(rows) > 10000:
            rows = rows[:10000]
            logger.warning("Chart data truncated to 10000 rows")
>>>>>>> master

        # Match column names case-insensitively
        if x_column.lower() not in normalized_cols or y_column.lower() not in normalized_cols:
            raise ValueError(f"'{x_column}' or '{y_column}' not in SQL result columns: {columns}")

        # Map back to actual index
        x_index = normalized_cols.index(x_column.lower())
        y_index = normalized_cols.index(y_column.lower())

<<<<<<< HEAD
        # Extract chart data
        labels = [row[x_index] for row in rows]
        values = [row[y_index] for row in rows]
=======
        # Extract chart data with validation
        labels = []
        values = []
        
        for row in rows:
            try:
                label = str(row[x_index]) if row[x_index] is not None else "N/A"
                value = float(row[y_index]) if row[y_index] is not None else 0
                labels.append(label)
                values.append(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid row: {row}, error: {e}")
                continue
>>>>>>> master

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
<<<<<<< HEAD
        print(f"[chart_handler.py] Chart generation failed: {e}")  # Optional for dev logs
        return {
            "type": "text",
            "text": f"⚠️ Chart generation failed: {str(e)}"
        }
=======
        logger.error(f"Chart generation failed: {e}")
        return {
            "type": "text",
            "text": f"⚠️ Chart generation failed: {str(e)}"
        }
>>>>>>> master
