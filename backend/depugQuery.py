# from app.core.db import engine
# from sqlalchemy import text
# import pandas as pd

# def debug_sales_data():
#     """Debug the sales data discrepancy"""
    
#     queries = {
#         "user_query": """
#             SELECT 
#                 customer_name_e, 
#                 SUM(sales_value) AS total_sales
#             FROM sales_data 
#             WHERE job_date >= '2024-01-01' AND job_date < '2025-01-01'
#             GROUP BY customer_name_e 
#             ORDER BY total_sales DESC 
#             LIMIT 5
#         """,
        
#         "bot_likely_query": """
#             SELECT 
#                 customer_name_e, 
#                 ROUND(SUM(sales_value), 3) AS total_sales
#             FROM sales_data 
#             WHERE tran_type = 'Sales' AND EXTRACT(YEAR FROM job_date) = 2024
#             GROUP BY customer_name_e 
#             ORDER BY total_sales DESC 
#             LIMIT 5
#         """,
        
#         "all_transactions_2024": """
#             SELECT 
#                 customer_name_e, 
#                 ROUND(SUM(sales_value), 3) AS total_sales
#             FROM sales_data 
#             WHERE EXTRACT(YEAR FROM job_date) = 2024
#             GROUP BY customer_name_e 
#             ORDER BY total_sales DESC 
#             LIMIT 5
#         """,
        
#         "debug_sultan_center": """
#             SELECT 
#                 tran_type,
#                 COUNT(*) as transaction_count,
#                 ROUND(SUM(sales_value), 3) as total_value
#             FROM sales_data 
#             WHERE customer_name_e = 'Sultan Center' 
#             AND EXTRACT(YEAR FROM job_date) = 2024
#             GROUP BY tran_type
#             ORDER BY total_value DESC
#         """,
        
#         "date_range_check": """
#             SELECT 
#                 MIN(job_date) as min_date,
#                 MAX(job_date) as max_date,
#                 COUNT(*) as total_records
#             FROM sales_data
#             WHERE EXTRACT(YEAR FROM job_date) = 2024
#         """,
        
#         "transaction_types": """
#             SELECT 
#                 tran_type,
#                 COUNT(*) as count,
#                 ROUND(SUM(sales_value), 3) as total_value
#             FROM sales_data 
#             WHERE EXTRACT(YEAR FROM job_date) = 2024
#             GROUP BY tran_type
#             ORDER BY total_value DESC
#         """
#     }
    
#     results = {}
    
#     with engine.connect() as conn:
#         for query_name, sql in queries.items():
#             try:
#                 result = conn.execute(text(sql))
#                 rows = result.fetchall()
#                 columns = list(result.keys())
                
#                 print(f"\n{'='*50}")
#                 print(f"QUERY: {query_name}")
#                 print(f"{'='*50}")
                
#                 # Convert to pandas for better display
#                 df = pd.DataFrame(rows, columns=columns)
#                 print(df.to_string(index=False))
                
#                 results[query_name] = df
                
#             except Exception as e:
#                 print(f"Error in {query_name}: {e}")
    
#     return results

# def analyze_discrepancy():
#     """Analyze the specific discrepancy"""
#     print("🔍 INVESTIGATING DATA DISCREPANCY")
#     print("=" * 60)
    
#     # Your exact query
#     user_query = """
#         SELECT 
#             customer_name_e, 
#             SUM(sales_value) AS total_sales
#         FROM sales_data 
#         WHERE job_date >= '2024-01-01' AND job_date < '2025-01-01'
#         GROUP BY customer_name_e 
#         ORDER BY total_sales DESC 
#         LIMIT 5
#     """
    
#     # What the bot might be generating
#     potential_bot_queries = [
#         # Query 1: With tran_type filter
#         """
#         SELECT 
#             customer_name_e, 
#             ROUND(SUM(sales_value), 3) AS total_sales
#         FROM sales_data 
#         WHERE tran_type = 'Sales' AND EXTRACT(YEAR FROM job_date) = 2024
#         GROUP BY customer_name_e 
#         ORDER BY total_sales DESC 
#         LIMIT 5
#         """,
        
#         # Query 2: Different date format
#         """
#         SELECT 
#             customer_name_e, 
#             ROUND(SUM(sales_value), 3) AS total_sales
#         FROM sales_data 
#         WHERE job_date >= '2024-01-01' AND job_date <= '2024-12-31'
#         GROUP BY customer_name_e 
#         ORDER BY total_sales DESC 
#         LIMIT 5
#         """,
        
#         # Query 3: Including all transaction types
#         """
#         SELECT 
#             customer_name_e, 
#             ROUND(SUM(sales_value), 3) AS total_sales
#         FROM sales_data 
#         WHERE EXTRACT(YEAR FROM job_date) = 2024
#         GROUP BY customer_name_e 
#         ORDER BY total_sales DESC 
#         LIMIT 5
#         """
#     ]
    
#     with engine.connect() as conn:
#         print("YOUR QUERY RESULTS:")
#         print("-" * 30)
#         result = conn.execute(text(user_query))
#         user_df = pd.DataFrame(result.fetchall(), columns=result.keys())
#         print(user_df.to_string(index=False))
        
#         print("\n\nPOTENTIAL BOT QUERIES:")
#         print("-" * 30)
        
#         for i, bot_query in enumerate(potential_bot_queries, 1):
#             print(f"\nBot Query {i}:")
#             try:
#                 result = conn.execute(text(bot_query))
#                 bot_df = pd.DataFrame(result.fetchall(), columns=result.keys())
#                 print(bot_df.to_string(index=False))
                
#                 # Check if this matches the bot output
#                 if len(bot_df) > 0:
#                     sultan_value = bot_df[bot_df['customer_name_e'] == 'Sultan Center']['total_sales'].iloc[0]
#                     if abs(float(sultan_value) - 2885345.738) < 1000:  # Close match
#                         print(f"🎯 MATCH FOUND! Bot Query {i} matches the bot output!")
                        
#             except Exception as e:
#                 print(f"Error in bot query {i}: {e}")

# if __name__ == "__main__":
#     analyze_discrepancy()
#     debug_sales_data()

# Debug script for quarter sales discrepancy

from app.core.db import engine
from sqlalchemy import text
import pandas as pd

def debug_quarter_sales():
    """Debug the quarter sales discrepancy"""
    
    queries = {
        "your_query_q2_2025": """
            SELECT
                salesman_name_e,
                SUM(sales_value) AS total_sales
            FROM sales_data
            WHERE job_date >= '2025-04-01' AND job_date <= '2025-06-30'
            GROUP BY salesman_name_e
            HAVING SUM(sales_value) > 100000
            ORDER BY total_sales DESC
        """,
        
        "bot_likely_q2_2025_sales_only": """
            SELECT
                salesman_name_e,
                ROUND(SUM(sales_value), 3) AS total_sales
            FROM sales_data
            WHERE tran_type = 'Sales' 
            AND job_date >= '2025-04-01' AND job_date <= '2025-06-30'
            GROUP BY salesman_name_e
            HAVING SUM(sales_value) > 100000
            ORDER BY total_sales DESC
        """,
        
        "q1_2025_all_transactions": """
            SELECT
                salesman_name_e,
                ROUND(SUM(sales_value), 3) AS total_sales
            FROM sales_data
            WHERE job_date >= '2025-01-01' AND job_date <= '2025-03-31'
            GROUP BY salesman_name_e
            HAVING SUM(sales_value) > 100000
            ORDER BY total_sales DESC
        """,
        
        "q1_2025_sales_only": """
            SELECT
                salesman_name_e,
                ROUND(SUM(sales_value), 3) AS total_sales
            FROM sales_data
            WHERE tran_type = 'Sales'
            AND job_date >= '2025-01-01' AND job_date <= '2025-03-31'
            GROUP BY salesman_name_e
            HAVING SUM(sales_value) > 100000
            ORDER BY total_sales DESC
        """,
        
        "current_quarter_dynamic": """
            SELECT
                salesman_name_e,
                ROUND(SUM(sales_value), 3) AS total_sales
            FROM sales_data
            WHERE EXTRACT(QUARTER FROM job_date) = EXTRACT(QUARTER FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM job_date) = EXTRACT(YEAR FROM CURRENT_DATE)
            GROUP BY salesman_name_e
            HAVING SUM(sales_value) > 100000
            ORDER BY total_sales DESC
        """,
        
        "debug_shabeer_q2": """
            SELECT 
                tran_type,
                COUNT(*) as transaction_count,
                ROUND(SUM(sales_value), 3) as total_value
            FROM sales_data 
            WHERE salesman_name_e = 'SHABEER MANZIL'
            AND job_date >= '2025-04-01' AND job_date <= '2025-06-30'
            GROUP BY tran_type
            ORDER BY total_value DESC
        """,
        
        "date_range_check_q2": """
            SELECT 
                MIN(job_date) as min_date,
                MAX(job_date) as max_date,
                COUNT(*) as total_records
            FROM sales_data
            WHERE job_date >= '2025-04-01' AND job_date <= '2025-06-30'
        """,
        
        "quarter_comparison": """
            SELECT 
                EXTRACT(QUARTER FROM job_date) as quarter,
                EXTRACT(YEAR FROM job_date) as year,
                tran_type,
                COUNT(*) as transactions,
                ROUND(SUM(sales_value), 3) as total_value
            FROM sales_data 
            WHERE EXTRACT(YEAR FROM job_date) = 2025
            GROUP BY EXTRACT(QUARTER FROM job_date), EXTRACT(YEAR FROM job_date), tran_type
            ORDER BY quarter, tran_type
        """
    }
    
    print("🔍 DEBUGGING QUARTER SALES DISCREPANCY")
    print("=" * 70)
    
    with engine.connect() as conn:
        for query_name, sql in queries.items():
            try:
                print(f"\n{'='*50}")
                print(f"QUERY: {query_name}")
                print(f"{'='*50}")
                
                result = conn.execute(text(sql))
                rows = result.fetchall()
                columns = list(result.keys())
                
                if rows:
                    df = pd.DataFrame(rows, columns=columns)
                    print(df.to_string(index=False))
                    
                    # Check for SHABEER MANZIL match
                    if 'salesman_name_e' in df.columns and 'total_sales' in df.columns:
                        shabeer_row = df[df['salesman_name_e'] == 'SHABEER MANZIL']
                        if not shabeer_row.empty:
                            shabeer_value = float(shabeer_row['total_sales'].iloc[0])
                            print(f"\n🎯 SHABEER MANZIL value: {shabeer_value:,.3f}")
                            
                            # Check if this matches bot output (426,583.286)
                            if abs(shabeer_value - 426583.286) < 1000:
                                print(f"🎯 MATCH FOUND! This query matches the bot output!")
                else:
                    print("No results returned")
                    
            except Exception as e:
                print(f"Error in {query_name}: {e}")

def analyze_last_quarter_logic():
    """Analyze what 'last quarter' means"""
    print("\n🗓️ ANALYZING 'LAST QUARTER' DEFINITION")
    print("=" * 50)
    
    # Different interpretations of "last quarter"
    quarter_queries = {
        "Q2_2025_manual": "job_date >= '2025-04-01' AND job_date <= '2025-06-30'",
        "Q1_2025_previous": "job_date >= '2025-01-01' AND job_date <= '2025-03-31'",
        "Q4_2024_last_complete": "job_date >= '2024-10-01' AND job_date <= '2024-12-31'",
        "Last_3_months": "job_date >= CURRENT_DATE - INTERVAL '3 months'",
        "Previous_quarter_dynamic": """
            EXTRACT(QUARTER FROM job_date) = EXTRACT(QUARTER FROM CURRENT_DATE) - 1
            AND EXTRACT(YEAR FROM job_date) = EXTRACT(YEAR FROM CURRENT_DATE)
        """
    }
    
    with engine.connect() as conn:
        for name, where_clause in quarter_queries.items():
            try:
                query = f"""
                    SELECT 
                        COUNT(*) as total_transactions,
                        COUNT(DISTINCT salesman_name_e) as unique_salespeople,
                        ROUND(SUM(sales_value), 3) as total_sales
                    FROM sales_data
                    WHERE {where_clause}
                """
                
                result = conn.execute(text(query))
                row = result.fetchone()
                
                print(f"\n{name}:")
                print(f"  Total transactions: {row[0]:,}")
                print(f"  Unique salespeople: {row[1]:,}")
                print(f"  Total sales: {row[2]:,.3f} KWD")
                
            except Exception as e:
                print(f"Error in {name}: {e}")

if __name__ == "__main__":
    debug_quarter_sales()
    analyze_last_quarter_logic()