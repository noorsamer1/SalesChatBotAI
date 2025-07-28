from .handlersCommnFunction import *

def handle_table(response):
    """Enhanced table handler with better formatting and insights"""
    try:
        sql = response.get("value_code", response.get("code", "")).strip()
        title = response.get("title", "Data Table")
        
        if not sql:
            return {
                "type": "text",
                "text": "⚠️ No SQL query provided for table"
            }
        
        try:
            rows, columns = execute_query_safely(sql, timeout=45)  # Longer timeout for tables
            
            # Smart data size validation - respect SQL LIMIT clauses
            import re
            sql_upper = sql.upper()
            
            # Check if query already has a reasonable LIMIT
            limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
            has_reasonable_limit = False
            
            if limit_match:
                limit_value = int(limit_match.group(1))
                has_reasonable_limit = limit_value <= 50  # Consider LIMIT 50 or less as reasonable
            
            # Only truncate if no reasonable limit and result is too large
            if not has_reasonable_limit and len(rows) > 1000:
                rows = rows[:1000]
                logger.warning(f"Table truncated to 1000 rows (no LIMIT clause found)")
                title += " (showing first 1000 rows - consider using LIMIT in query)"
            elif len(rows) > 0:
                logger.info(f"Table generated with {len(rows)} rows")
            
            # Convert rows to proper format
            formatted_rows = []
            for row in rows:
                formatted_row = []
                for i, value in enumerate(row):
                    if value is None:
                        formatted_row.append("")
                    elif isinstance(value, (int, float, Decimal)):
                        # Format based on column name
                        col_name = columns[i].lower()
                        if any(keyword in col_name for keyword in ['sales', 'revenue', 'profit', 'value', 'amount', 'discount', 'loss', 'return']):
                            formatted_row.append(format_currency(value))
                        elif any(keyword in col_name for keyword in ['percent', 'margin', 'rate']):
                            formatted_row.append(f"{float(value):.1f}%")
                        elif any(keyword in col_name for keyword in ['qty', 'quantity', 'count']):
                            formatted_row.append(f"{int(value):,}")
                        else:
                            formatted_row.append(str(value))
                    else:
                        formatted_row.append(str(value))
                formatted_rows.append(formatted_row)
            
            result = {
                "type": "table",
                "title": title,
                "columns": columns,
                "rows": formatted_rows
            }
            
            return add_business_context(result, "table")
            
        except TimeoutError:
            return {
                "type": "text",
                "text": "⚠️ Query took too long to execute. Please try a more specific question."
            }
        except Exception as e:
            logger.error(f"Table query error: {e}")
            print(f"[TABLE HANDLER] SQL Error: {e}")
            print(f"[TABLE HANDLER] Failed SQL: {sql}")
            return {
                "type": "text",
                "text": f"⚠️ Database error: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"Table handler error: {e}")
        return {
            "type": "text",
            "text": f"⚠️ Error processing table: {str(e)}"
        }