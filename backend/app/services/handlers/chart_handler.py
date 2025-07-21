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

        # Enhanced handling for new chart types
        if isinstance(x_column, list):
            x_column = x_column[0] if x_column else None
            print(f"[CHART HANDLER] Fixed x_column from list: {x_column}")
        
        # Handle multiple y-columns for stacked_bar and multi_line charts
        y_columns = []
        if isinstance(y_column, list):
            y_columns = y_column
            y_column = y_column[0] if y_column else None
            print(f"[CHART HANDLER] Multi-column chart detected: {y_columns}")
        else:
            y_columns = [y_column] if y_column else []

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

        # 🚀 NEW: Detect multi-series data for year-over-year comparisons
        year_columns = []
        profit_columns = []
        
        # Look for patterns like sales_2023, sales_2024, profit_2023, profit_2024
        for col in columns:
            if any(pattern in col.lower() for pattern in ['sales_20', 'revenue_20']) and any(year in col for year in ['2022', '2023', '2024', '2025']):
                year_columns.append(col)
            elif any(pattern in col.lower() for pattern in ['profit_20']) and any(year in col for year in ['2022', '2023', '2024', '2025']):
                profit_columns.append(col)
        
        # Check if this is a multi-series comparison chart
        is_multi_series = len(year_columns) >= 2
        
        print(f"[CHART HANDLER] Multi-series detection: {is_multi_series}, Year columns: {year_columns}")

        # Match column names case-insensitively
        if x_column.lower() not in normalized_cols:
            error_msg = f"X-axis column '{x_column}' not in SQL result columns: {columns}"
            logger.error(error_msg)
            return {
                "type": "text",
                "text": f"⚠️ Column mismatch: {error_msg}"
            }

        # Map back to actual index
        x_index = normalized_cols.index(x_column.lower())

        # Extract chart data with validation
        labels = []
        
        for row in rows:
            try:
                label = str(row[x_index]) if row[x_index] is not None else "N/A"
                labels.append(label)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid row: {row}, error: {e}")
                continue

        if not labels:
            return {
                "type": "text",
                "text": "⚠️ No valid chart data found in query results. This may indicate missing data for the requested time period."
            }

        # 🚀 NEW: Handle multi-series data differently
        if is_multi_series and chart_kind == "line":
            # Multi-series line chart for year-over-year comparisons
            series_data = []
            
            for col in year_columns:
                if col.lower() in normalized_cols:
                    col_index = normalized_cols.index(col.lower())
                    values = []
                    
                    for row in rows:
                        try:
                            value = float(row[col_index]) if row[col_index] is not None else 0
                            values.append(value)
                        except (ValueError, TypeError):
                            values.append(0)
                    
                    # Extract year from column name (e.g., sales_2024 -> 2024)
                    year = col.split('_')[-1] if '_' in col else col
                    series_data.append({
                        "name": year,
                        "values": values,
                        "color": "#667eea" if "2023" in col else "#10b981" if "2024" in col else "#f59e0b"
                    })
            
            # Check for meaningful data (not all zeros)
            all_values = [val for series in series_data for val in series["values"]]
            if all(v == 0 for v in all_values):
                return {
                    "type": "text", 
                    "text": f"⚠️ Chart data contains only zero values. This suggests no sales data exists for the requested period. Please check if data is available for the specified years/months."
                }
            
            result = {
                "type": "chart",
                "title": chart_title,
                "chart_data": {
                    "labels": labels,
                    "series": series_data,  # Multiple series for comparison
                    "x_axis": x_column,
                    "y_axis": "Sales Value (KWD)",
                    "multi_series": True
                },
                "kind": chart_kind
            }
            
            print(f"[CHART HANDLER] Multi-series output: {result}")
            return result
            
        # Handle multiple series charts (stacked_bar, multi_line)
        elif len(y_columns) > 1 and chart_kind in ["stacked_bar", "multi_line"]:
            # Multi-series chart with multiple y-columns
            series_data = {}
            
            for y_col in y_columns:
                if y_col.lower() not in normalized_cols:
                    logger.warning(f"Y-column '{y_col}' not found in result, skipping")
                    continue
                    
                y_index = normalized_cols.index(y_col.lower())
                values = []
                
                for row in rows:
                    try:
                        value = float(row[y_index]) if row[y_index] is not None else 0
                        values.append(value)
                    except (ValueError, TypeError):
                        values.append(0)
                
                series_data[y_col] = values
            
            if not series_data:
                return {
                    "type": "text",
                    "text": "⚠️ No valid data columns found for multi-series chart."
                }
            
            result = {
                "type": "chart", 
                "title": chart_title,
                "chart_data": {
                    "labels": labels,
                    "values": series_data,  # Dictionary of series_name: values
                    "y": y_columns,  # Array of column names
                    "x_axis": x_column,
                    "y_axis": "Multiple Metrics",
                    "multi_series": True
                },
                "kind": chart_kind
            }
            
            print(f"[CHART HANDLER] Multi-series output: {result}")
            return result
            
        else:
            # Single-series chart (original logic)
            if y_column.lower() not in normalized_cols:
                error_msg = f"Y-axis column '{y_column}' not in SQL result columns: {columns}"
                logger.error(error_msg)
                return {
                    "type": "text",
                    "text": f"⚠️ Column mismatch: {error_msg}"
                }
            
            y_index = normalized_cols.index(y_column.lower())
            values = []
            
            for row in rows:
                try:
                    value = float(row[y_index]) if row[y_index] is not None else 0
                    values.append(value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid row: {row}, error: {e}")
                    values.append(0)

            # Check for meaningful data (not all zeros)
            if all(v == 0 for v in values):
                return {
                    "type": "text", 
                    "text": f"⚠️ Chart data contains only zero values. This suggests no sales data exists for the requested period. Please check if data is available for the specified years/months."
                }

            # Special handling for new chart types
            chart_data = {
                "labels": labels,
                "values": values,
                "x_axis": x_column,
                "y_axis": y_column,
                "multi_series": False
            }
            
            # Add special data for specific chart types
            if chart_kind == "heatmap":
                # For heatmaps, we need a 2D matrix - this is a simplified example
                chart_data["matrix"] = [values[i:i+3] for i in range(0, len(values), 3)] if len(values) >= 3 else [values]
                chart_data["x_labels"] = labels[:3] if len(labels) >= 3 else labels
                chart_data["y_labels"] = ["Metric A", "Metric B", "Metric C"][:len(chart_data["matrix"])]
            
            # Return frontend-friendly format
            result = {
                "type": "chart",
                "title": chart_title,
                "chart_data": chart_data,
                "kind": chart_kind
            }

            print(f"[CHART HANDLER] Single-series output: {result}")
            return result

    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        return {
            "type": "text",
            "text": f"⚠️ Chart generation failed: {str(e)}"
        }