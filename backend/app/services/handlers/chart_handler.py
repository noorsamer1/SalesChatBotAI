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

        # Match column names case-insensitively
        if x_column.lower() not in normalized_cols or y_column.lower() not in normalized_cols:
            raise ValueError(f"'{x_column}' or '{y_column}' not in SQL result columns: {columns}")

        # Map back to actual index
        x_index = normalized_cols.index(x_column.lower())
        y_index = normalized_cols.index(y_column.lower())

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
        logger.error(f"Chart generation failed: {e}")
        return {
            "type": "text",
            "text": f"⚠️ Chart generation failed: {str(e)}"
        }