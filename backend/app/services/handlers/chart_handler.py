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

        print(f"[CHART HANDLER] Input: {response}")  # Debug log

        # Fix: Handle case where x or y might be lists (LLM error)
        if isinstance(x_column, list):
            x_column = x_column[0] if x_column else None
            print(f"[CHART HANDLER] Fixed x_column from list: {x_column}")
        
        if isinstance(y_column, list):
            y_column = y_column[0] if y_column else None
            print(f"[CHART HANDLER] Fixed y_column from list: {y_column}")

        # Convert to strings to prevent attribute errors
        x_column = str(x_column) if x_column else None
        y_column = str(y_column) if y_column else None

        if not (sql and x_column and y_column):
            raise ValueError(f"Missing 'code', 'x', or 'y' in chart response. Got x='{x_column}', y='{y_column}'")

        try:
            # Execute the SQL safely with timeout
            rows, columns = execute_query_with_timeout(sql, timeout=30)
            normalized_cols = [col.lower() for col in columns]
            print(f"[CHART HANDLER] Query returned {len(rows)} rows with columns: {columns}")
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
            error_msg = f"'{x_column}' or '{y_column}' not in SQL result columns: {columns}"
            logger.error(error_msg)
            return {
                "type": "text",
                "text": f"⚠️ Column mismatch: {error_msg}"
            }

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

        if not labels or not values:
            return {
                "type": "text",
                "text": "⚠️ No valid chart data found in query results. This may indicate missing data for the requested time period."
            }

        # Check for meaningful data (not all zeros)
        if all(v == 0 for v in values):
            return {
                "type": "text", 
                "text": f"⚠️ Chart data contains only zero values. This suggests no sales data exists for the requested period. Please check if data is available for the specified years/months."
            }

        # Return frontend-friendly format - FIXED FORMAT
        result = {
            "type": "chart",
            "title": chart_title,
            "chart_data": {
                "labels": labels,  # Array of labels for x-axis
                "values": values,  # Array of values for y-axis
                "x_axis": x_column,  # Column name for x-axis
                "y_axis": y_column   # Column name for y-axis
            },
            "kind": chart_kind
        }

        print(f"[CHART HANDLER] Output: {result}")  # Debug log
        return result

    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        return {
            "type": "text",
            "text": f"⚠️ Chart generation failed: {str(e)}"
        }