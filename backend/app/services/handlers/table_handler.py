<<<<<<< HEAD
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
=======
from .handlersCommnFunction import *

def handle_table(response):
    """Enhanced table handler with better formatting and insights"""
    try:
        sql = response.get("code", "").strip()
        title = response.get("title", "Data Table")
        
        if not sql:
            return {
                "type": "text",
                "text": "⚠️ No SQL query provided for table"
            }
        
        try:
            rows, columns = execute_query_safely(sql, timeout=45)  # Longer timeout for tables
            
            # Validate data size
            if len(rows) > 1000:
                rows = rows[:1000]
                logger.warning(f"Table truncated to 1000 rows")
                title += " (showing first 1000 rows)"
            
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
                        if any(keyword in col_name for keyword in ['sales', 'revenue', 'profit', 'value', 'amount','discount']):
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
>>>>>>> master
