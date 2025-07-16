from app.core.db import engine
from sqlalchemy import text
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import re

def get_smart_context(user_input: str) -> dict:
    """Generate smart context based on user query patterns"""
    context = {
        "time_period": "current_year",
        "focus_area": "general",
        "comparison_needed": False,
        "top_n": 10
    }
    
    # Time period detection
    if any(word in user_input.lower() for word in ["ytd", "year to date", "this year"]):
        context["time_period"] = "ytd"
    elif any(word in user_input.lower() for word in ["mtd", "month to date", "this month"]):
        context["time_period"] = "mtd"
    elif any(word in user_input.lower() for word in ["last month", "previous month"]):
        context["time_period"] = "last_month"
    elif any(word in user_input.lower() for word in ["2023", "2024"]):
        year_match = re.search(r'20\d{2}', user_input)
        if year_match:
            context["time_period"] = f"year_{year_match.group()}"
    
    # Focus area detection
    if any(word in user_input.lower() for word in ["customer", "client"]):
        context["focus_area"] = "customer"
    elif any(word in user_input.lower() for word in ["product", "item", "brand"]):
        context["focus_area"] = "product"
    elif any(word in user_input.lower() for word in ["sales", "salesman", "salespeople"]):
        context["focus_area"] = "salesperson"
    elif any(word in user_input.lower() for word in ["division", "department"]):
        context["focus_area"] = "division"
    elif any(word in user_input.lower() for word in ["return", "refund"]):
        context["focus_area"] = "returns"
    
    # Comparison detection
    if any(word in user_input.lower() for word in ["vs", "versus", "compare", "comparison", "trend"]):
        context["comparison_needed"] = True
    
    # Top N detection
    top_n_match = re.search(r'top\s+(\d+)', user_input.lower())
    if top_n_match:
        context["top_n"] = int(top_n_match.group(1))
    elif any(word in user_input.lower() for word in ["top", "best", "highest"]):
        context["top_n"] = 5
    
    return context

def get_business_insights() -> str:
    """Generate current business insights from recent data"""
    try:
        with engine.connect() as conn:
            # Get current year performance
            current_year_query = """
            SELECT 
                ROUND(SUM(CASE WHEN tran_type = 'Sales' THEN sales_value END), 3) as current_sales,
                ROUND(SUM(CASE WHEN tran_type = 'Sales Return' THEN ABS(sales_value) END), 3) as current_returns,
                COUNT(DISTINCT customer_name_e) as active_customers,
                COUNT(DISTINCT salesman_name_e) as active_salespeople
            FROM sales_data 
            WHERE EXTRACT(YEAR FROM job_date) = EXTRACT(YEAR FROM CURRENT_DATE)
            """
            
            result = conn.execute(text(current_year_query)).fetchone()
            
            if result:
                return f"""
Current Business Context (YTD {datetime.now().year}):
- Total Sales: {result.current_sales or 0} KWD
- Total Returns: {result.current_returns or 0} KWD
- Active Customers: {result.active_customers or 0}
- Active Salespeople: {result.active_salespeople or 0}
- Return Rate: {((result.current_returns or 0) / (result.current_sales or 1)) * 100:.1f}%
"""
    except Exception as e:
        print(f"Error getting business insights: {e}")
        return "Business context unavailable."

def get_seasonal_context() -> str:
    """Get seasonal business context"""
    current_month = datetime.now().month
    
    seasonal_insights = {
        1: "New Year period - typically slower sales, focus on promotions",
        2: "Valentine's season - boost in gift items and confectionery",
        3: "Spring season - cleaning supplies and fresh products trend up",
        4: "Ramadan preparation - significant increase in food and beverage sales",
        5: "Post-Ramadan - Eid shopping surge, fashion and electronics peak",
        6: "Summer start - cooling products and beverages in high demand",
        7: "Mid-summer - peak cooling season, maintenance products surge",
        8: "Summer continuation - sustained demand for cooling products",
        9: "Back-to-school - stationery, electronics, and clothing peak",
        10: "Fall season - moderate sales across categories",
        11: "Pre-holiday - gift items and electronics start trending up",
        12: "Holiday season - peak sales period across all categories"
    }
    
    return f"Seasonal Context ({datetime.now().strftime('%B')}): {seasonal_insights.get(current_month, 'Regular business period')}"

def build_final_prompt(user_input: str, conversation_history: list = None, base_prompt_path: str = "prompts/system_prompt.txt") -> str:
    """Build enhanced prompt with smart context and business intelligence"""
    
    # Load base prompt
    try:
        base_prompt = Path(base_prompt_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        # Fallback if file not found
        base_prompt = """You are FutureTec, an advanced AI sales analytics assistant.
        Database tables: $table_names
        Sample data: $sample_data
        
        Provide JSON responses for sales analytics questions only."""
    
    # Get smart context
    context = get_smart_context(user_input)
    
    # Get table schema and sample data
    try:
        with engine.connect() as conn:
            # Get table names
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name NOT IN ('users', 'conversations', 'messages')
            """))
            tables = [row[0] for row in result.fetchall()]
            table_names_str = ", ".join(tables)
            
            # Get sample data (focus on sales_data)
            preview_blocks = []
            for table in tables:
                if table == 'sales_data':
                    # Get more comprehensive sample for main table
                    df = pd.read_sql_query(f"""
                        SELECT tran_type, customer_name_e, salesman_name_e, brandname, item_name_e, 
                               sales_value, sales_qty, sales_prof, job_date, division_name
                        FROM {table} 
                        WHERE job_date >= CURRENT_DATE - INTERVAL '90 days'
                        ORDER BY job_date DESC 
                        LIMIT 5
                    """, con=engine)
                else:
                    df = pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT 3', con=engine)
                
                markdown_table = df.to_markdown(index=False)
                preview_blocks.append(f"Table: {table}\n{markdown_table}\n")
                
    except Exception as e:
        print(f"Error building prompt: {e}")
        table_names_str = "sales_data"
        preview_blocks = ["Error loading sample data"]
    
    preview_str = "\n".join(preview_blocks)
    
    # Add conversation history if provided
    history_context = ""
    if conversation_history and len(conversation_history) > 0:
        recent_messages = conversation_history[-3:]  # Last 3 messages
        history_items = []
        for msg in recent_messages:
            if msg.get('sender') == 'user':
                history_items.append(f"Previous Query: {msg.get('content', '')}")
        
        if history_items:
            history_context = f"\n\nConversation Context:\n" + "\n".join(history_items)
    
    # Build smart query hints based on context
    smart_hints = f"""
Query Context Analysis:
- Time Focus: {context['time_period']}
- Business Area: {context['focus_area']}
- Comparison Needed: {context['comparison_needed']}
- Results Limit: Top {context['top_n']}

{get_business_insights()}

{get_seasonal_context()}

Smart Query Suggestions:
- For customer analysis: Include purchase frequency, recency, and lifetime value
- For product analysis: Show profit margins, inventory turnover, seasonal trends
- For sales team: Include target achievement, territory performance, growth rates
- For time analysis: Include year-over-year comparisons and growth percentages
- Always provide actionable business insights alongside raw data
"""
    
    # Replace placeholders
    filled_prompt = (
        base_prompt
        .replace("$table_names", table_names_str)
        .replace("$sample_data", preview_str)
        + smart_hints
        + history_context
        + f"\n\nCurrent Query: {user_input}"
    )
    
    return filled_prompt

def get_query_complexity_score(user_input: str) -> int:
    """Score query complexity to adjust response depth"""
    score = 1
    
    # Complex analysis keywords
    complex_keywords = [
        "analysis", "analyze", "trend", "comparison", "performance", 
        "insights", "correlation", "forecast", "predict", "optimize"
    ]
    
    if any(keyword in user_input.lower() for keyword in complex_keywords):
        score += 2
    
    # Time-based complexity
    if any(word in user_input.lower() for word in ["month", "year", "quarter", "ytd", "mtd"]):
        score += 1
    
    # Multiple entity complexity
    entities = ["customer", "product", "sales", "brand", "division"]
    entity_count = sum(1 for entity in entities if entity in user_input.lower())
    score += entity_count
    
    return min(score, 5)  # Cap at 5