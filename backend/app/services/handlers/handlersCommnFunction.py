# Enhanced handlers with cross-platform timeout support

from app.core.db import engine
from sqlalchemy import text
import time
import concurrent.futures
from decimal import Decimal
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    pass

def execute_query_safely(sql: str, timeout: int = 30) -> tuple[list, list]:
    """Execute SQL query safely with cross-platform timeout"""
    if not sql.strip():
        raise ValueError("Empty SQL query")
    
    # Additional safety checks
    dangerous_patterns = [
        r'\bDELETE\b', r'\bDROP\b', r'\bTRUNCATE\b', r'\bALTER\b',
        r'\bCREATE\b', r'\bINSERT\b', r'\bUPDATE\b', r'\bEXEC\b'
    ]
    
    import re
    for pattern in dangerous_patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            raise ValueError(f"Query contains dangerous operation: {pattern}")
    
    def run_query():
        with engine.connect() as conn:
            # Set connection-level timeout (PostgreSQL)
            try:
                conn.execute(text(f"SET statement_timeout = '{timeout}s'"))
            except Exception:
                pass  # Some databases don't support this
            
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
            return rows, columns
    
    # Use concurrent.futures for cross-platform timeout
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_query)
        try:
            rows, columns = future.result(timeout=timeout)
            logger.info(f"Query executed successfully: {len(rows)} rows returned")
            return rows, columns
        except concurrent.futures.TimeoutError:
            logger.error(f"Query timed out after {timeout} seconds")
            raise TimeoutError(f"Query took too long to execute (>{timeout}s)")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return [], []
def format_currency(value) -> str:
    """Format currency values consistently"""
    if value is None:
        return "0.000"
    
    if isinstance(value, (int, float, Decimal)):
        return f"{float(value):,.3f}"
    
    try:
        return f"{float(value):,.3f}"
    except (ValueError, TypeError):
        return str(value)

def format_large_number(value) -> str:
    """Format large numbers with abbreviations"""
    if value is None:
        return "0"
    
    try:
        num_val = float(value)
        if abs(num_val) >= 1_000_000:
            return f"{num_val/1_000_000:.1f}M"
        elif abs(num_val) >= 1_000:
            return f"{num_val/1_000:.1f}K"
        else:
            return f"{num_val:.1f}"
    except (ValueError, TypeError):
        return str(value)

def add_business_context(data: dict, response_type: str) -> dict:
    """Add business context and insights to responses"""
    if response_type == "table" and "rows" in data:
        # Add summary statistics for tables
        if len(data["rows"]) > 0:
            data["summary"] = {
                "total_rows": len(data["rows"]),
                "columns": len(data["columns"]),
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    elif response_type == "chart" and "chart_data" in data:
        # Add insights for charts
        values = data["chart_data"].get("values", [])
        if values:
            data["insights"] = {
                "max_value": max(values),
                "min_value": min(values),
                "avg_value": sum(values) / len(values),
                "trend": "increasing" if values[-1] > values[0] else "decreasing"
            }
    
    return data