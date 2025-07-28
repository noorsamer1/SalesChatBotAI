from app.core.db import engine
from sqlalchemy import text
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import re

# Allowed chart types for Smart Visualization AI
ALLOWED_CHART_TYPES = {"bar", "line", "donut", "horizontal_bar", "stacked_bar", "waterfall", "gauge", "multi_line"}

# Modular prompt sections for dynamic injection
PROMPT_MODULES = {
    "core_rules": """
You are FutureTec, the world's most advanced AI sales analytics assistant specialized in Kuwait market retail analytics.

**🚨 CRITICAL RULES - MUST FOLLOW:**
1. **RESPONSE FORMAT**: Every response MUST be valid JSON array: `[{"type": "text"}, {"type": "table/chart"}]`
2. **PLACEHOLDER DETECTION**: "Product X" = ask clarification. "SKUs" = analyze all products. NEVER ask about "SKUs"!
3. **YEAR LOGIC**: No year specified = 2025. "Last year" = 2024. "Promotional campaigns" = 2025.
4. **GREETING HANDLING**: "hello", "help" = immediate hardcoded JSON response. NO LLM calls.
5. **BUSINESS CONTEXT**: NEVER return tables without strategic analysis text block.
6. **TABLE LIMITS**: ALWAYS use LIMIT 10-20 for readability. Charts MUST have limits.
""",
    
    "database_schema": """
**📊 DATABASE SCHEMA (sales_data table):**
- **Organizational**: division_name, manager_name, salesman_name_e
- **Customer**: customer_name_e, customer_name_e_child  
- **Product**: item_name_e, brandname, item_rec_name
- **Financial**: sales_value, sales_qty, sales_prof, actual_discount_value
- **Temporal**: yy (year), mm (month), job_date
- **Operational**: tran_type ('Sales'/'Sales Return'), warehouse_name, promo ('Y'/N)
- **Returns**: sr_reason_description, ABS(sales_value) for return amounts
""",
    
    "chart_rules": """
**🎨 CHART TYPE SELECTION:**
- **horizontal_bar**: Long names (salespeople, customers, products)
- **line**: Time series, trends, monthly/yearly data
- **donut**: Market share, composition, percentages  
- **stacked_bar**: Breakdowns by category
- **multi_line**: Multiple metrics over time
- **waterfall**: Change analysis, growth breakdown

**Chart JSON Format:**
```json
{
  "type": "chart",
  "title": "Chart Title",
  "code": "SELECT x_col, y_col FROM...",
  "x": "x_col",
  "y": "y_col", 
  "kind": "chart_type"
}
```
""",
    
    "returns_analysis": """
**🔄 RETURNS DATA RULES:**
When user mentions "returns" in analysis, MUST include:
- `return_loss`: `ROUND(SUM(CASE WHEN tran_type = 'Sales Return' THEN ABS(sales_value) ELSE 0 END), 3)`
- `return_rate_pct`: `ROUND((SUM(CASE WHEN tran_type = 'Sales Return' THEN ABS(sales_value) ELSE 0 END) / NULLIF(SUM(CASE WHEN tran_type = 'Sales' THEN sales_value ELSE 0 END), 0)) * 100, 1)`

**Brand Analysis with Returns Template:**
```sql
SELECT brandname, total_sales, total_volume, growth_pct, total_profit, profit_margin_pct,
       ROUND(SUM(CASE WHEN tran_type = 'Sales Return' THEN ABS(sales_value) ELSE 0 END), 3) as return_loss,
       ROUND((SUM(CASE WHEN tran_type = 'Sales Return' THEN ABS(sales_value) ELSE 0 END) / NULLIF(SUM(CASE WHEN tran_type = 'Sales' THEN sales_value ELSE 0 END), 0)) * 100, 1) as return_rate_pct
FROM sales_data WHERE yy IN (2023, 2024) GROUP BY brandname ORDER BY total_sales DESC LIMIT 10
```
""",
    
    "few_shot_examples": """
**🧠 EXAMPLE PATTERNS - MIMIC THESE:**

**Underperforming SKUs:**
```json
[
  {"type": "text", "template": "Analyzing underperforming SKUs for 2025...", "value_code": ""},
  {"type": "table", "title": "Underperforming SKUs (2025)", "code": "SELECT item_name_e, ROUND(SUM(sales_value), 3) as total_sales FROM sales_data WHERE yy = 2025 GROUP BY item_name_e HAVING SUM(sales_value) < 50000 ORDER BY total_sales ASC LIMIT 20"}
]
```

**Top Performers:**
```json
[
  {"type": "text", "template": "Top 10 analysis shows strong performance...", "value_code": ""},
  {"type": "table", "title": "Top 10 Results", "code": "SELECT entity, ROUND(SUM(sales_value), 3) as total_sales FROM sales_data GROUP BY entity ORDER BY total_sales DESC LIMIT 10"}
]
```
""",
    
    "greeting_responses": """
**GREETING TEMPLATES:**
```json
[{"type": "text", "template": "Hello! I'm FutureTec, your AI sales analytics assistant. What would you like to explore today?", "value_code": ""}]
```
""",
    
    "business_definitions": """
**📚 BUSINESS METRICS:**
- **Listing Percentage**: (Items sold from brand / Total items in brand) × 100
- **Brand Mix**: (Brand sales / Total sales across all brands) × 100  
- **Return Rate**: (Return Loss / Gross Sales) × 100
- **Profit Margin**: (Profit / Sales) × 100
- **Growth Rate**: ((Current - Previous) / Previous) × 100
"""
}

def load_prompt_module(module_name: str) -> str:
    """Load a prompt module from file"""
    try:
        module_path = f"prompts/modules/{module_name}.txt"
        with open(module_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"[PROMPT MODULE] Warning: {module_name}.txt not found, using fallback")
        # Fallback to in-memory modules if files don't exist
        return PROMPT_MODULES.get(module_name, f"# {module_name} module not available")

def get_relevant_prompt_sections(user_input: str, intent_analysis: dict = None, conversation_history: list = None) -> str:
    """Load relevant sections from modular prompt files based on user intent"""
    
    user_lower = user_input.lower()
    selected_modules = []
    
    # CORE MODULES (always included)
    selected_modules.extend([
        "core_identity",
        "mandatory_response_format",
        "database_schema",  # Always include database schema for SQL generation
        "sql_rules"         # Always include SQL rules for proper queries
    ])
    
    # CONDITIONAL MODULES based on query analysis
    
    # Placeholder detection for queries with generic terms
    placeholder_indicators = ['product x', 'customer y', 'division a', 'item x']
    if any(indicator in user_lower for indicator in placeholder_indicators):
        selected_modules.append("placeholder_detection")
    
    # Dashboard/comprehensive analysis (priority trigger)
    dashboard_keywords = ['dashboard', 'comprehensive', 'overview', 'summary', 'trends']
    if any(keyword in user_lower for keyword in dashboard_keywords):
        selected_modules.append("business_intelligence")
    
    # Brand/product analysis
    brand_keywords = ['brand', 'brands', 'performers', 'top', 'product', 'item', 'sku']
    if any(keyword in user_lower for keyword in brand_keywords):
        selected_modules.append("business_intelligence")
    
    # Channel/division/sales analysis
    channel_keywords = ['channel', 'division', 'sales', 'split', 'breakdown', 'segment', 'customer']
    if any(keyword in user_lower for keyword in channel_keywords):
        selected_modules.append("business_intelligence")
    
    # Returns analysis
    if 'return' in user_lower:
        selected_modules.append("returns_analysis")
    
    # Chart/visualization requests  
    chart_keywords = ['chart', 'graph', 'visualization', 'show as', 'convert to', 'plot', 'pie', 'donut', 'doughnut', 'bar', 'line']
    if any(keyword in user_lower for keyword in chart_keywords):
        selected_modules.append("chart_guidelines")
    
    # Year/time analysis
    time_keywords = ['2024', '2023', '2025', 'year', 'last', 'this', 'quarter', 'month']
    if any(keyword in user_lower for keyword in time_keywords):
        selected_modules.append("year_date_logic")
    
    # Follow-up/format conversion (enhanced)
    followup_keywords = ['show as', 'convert to', 'give me', 'format', 'table', 'pie', 'donut', 'chart', 'as a']
    if any(keyword in user_lower for keyword in followup_keywords):
        selected_modules.append("follow_up_behaviors")
    
    # Business definitions for metrics queries
    metrics_keywords = ['margin', 'growth', 'performance', 'target', 'listing', 'mix']
    if any(keyword in user_lower for keyword in metrics_keywords):
        selected_modules.append("definition_rules")
    
    # Response format rules for complex queries
    complex_keywords = ['performers', 'analysis', 'compare', 'breakdown', 'insights']
    if any(keyword in user_lower for keyword in complex_keywords):
        selected_modules.append("response_format_rules")
    
    # Remove duplicates while preserving order
    unique_modules = []
    for module in selected_modules:
        if module not in unique_modules:
            unique_modules.append(module)
    
    # Load and combine selected modules
    combined_sections = []
    for module_name in unique_modules:
        try:
            with open(f"prompts/modules/{module_name}.txt", 'r', encoding='utf-8') as f:
                content = f.read().strip()
                combined_sections.append(content)
                print(f"[MODULAR PROMPT] Loaded: {module_name}")
        except FileNotFoundError:
            print(f"[MODULAR PROMPT] Warning: {module_name}.txt not found")
            continue
    
    final_prompt = "\n\n".join(combined_sections)
    
    # Add recent conversation context if available
    if conversation_history and len(conversation_history) > 0:
        try:
            context_items = []
            for item in conversation_history[-2:]:  # Only last 2 messages
                if isinstance(item, dict):
                    content = item.get('content', str(item))
                    sender = item.get('sender', 'unknown')
                    context_items.append(f"{sender}: {content}")
                elif isinstance(item, str):
                    context_items.append(item)
                else:
                    context_items.append(str(item))
            if context_items:
                recent_context = "\n".join(context_items)
                final_prompt += f"\n\n**RECENT CONTEXT:** {recent_context}"
        except Exception as e:
            print(f"[MODULAR PROMPT] Context processing error: {e}")
            pass
    
    print(f"[MODULAR PROMPT] Selected modules: {unique_modules}")
    print(f"[MODULAR PROMPT] Final prompt size: {len(final_prompt)} chars")
    
    return final_prompt

def get_smart_context(user_input: str) -> dict:
    """Generate smart context based on user query patterns"""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
    # 🎯 PLACEHOLDER DETECTION - Flag when user uses generic placeholders
    placeholder_patterns = [
        r'\bproduct\s+[xyz]\b',
        r'\bitem\s+[xyz]\b', 
        r'\bcustomer\s+[xyz]\b',
        r'\bclient\s+[xyz]\b',
        r'\bdivision\s+[xyz]\b',
        r'\bbrand\s+[xyz]\b'
    ]
    
    # 🚨 EXCLUDE common business terms that aren't placeholders
    business_terms = ['skus', 'all brands', 'all products', 'all customers', 'all divisions', 'by brand', 'all brand', 'every brand', 'each brand', 'underperforming', 'which skus', 'what skus']
    user_lower = user_input.lower()
    is_business_term = any(term in user_lower for term in business_terms)
    
    context = {
        "time_period": "current_year",
        "focus_area": "general",
        "comparison_needed": False,
        "top_n": 10,
        "has_placeholder": any(re.search(pattern, user_input.lower()) for pattern in placeholder_patterns) and not is_business_term
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

def get_proactive_business_insights(user_input: str, context: dict) -> dict:
    """Generate proactive business insights based on query patterns"""
    insights = {
        "business_alerts": [],
        "optimization_suggestions": [],
        "risk_indicators": [],
        "growth_opportunities": []
    }
    
    user_lower = user_input.lower()
    
    # Performance-based insights
    if any(word in user_lower for word in ["top", "best", "highest"]) and "salesman" in user_lower:
        insights["optimization_suggestions"].extend([
            "Consider analyzing what makes top performers successful",
            "Review training programs for lower performers",
            "Evaluate territory assignments and resource allocation"
        ])
        
    if "return" in user_lower or "refund" in user_lower:
        insights["business_alerts"].extend([
            "High return rates may indicate quality issues",
            "Consider vendor quality assessments",
            "Review customer satisfaction metrics"
        ])
        insights["risk_indicators"].append("Product quality monitoring needed")
        
    if "customer" in user_lower and any(word in user_lower for word in ["top", "best", "highest"]):
        insights["growth_opportunities"].extend([
            "Analyze customer retention strategies",
            "Consider customer loyalty programs", 
            "Evaluate upselling opportunities with top customers"
        ])
        
    if "profit" in user_lower and "low" in user_lower:
        insights["business_alerts"].extend([
            "Low profit margins require immediate attention",
            "Review pricing strategies and cost structure",
            "Analyze competitor pricing and positioning"
        ])
        
    # Seasonal/temporal insights
    if context.get("seasonal_context"):
        insights["optimization_suggestions"].extend([
            "Plan inventory based on seasonal patterns",
            "Adjust staffing for peak periods",
            "Develop seasonal marketing campaigns"
        ])
    
    return insights

def get_real_time_business_alerts(user_input: str) -> dict:
    """Business Intelligence Alert System adapted for 2023-2025 historical data analysis"""
    try:
        with engine.connect() as conn:
            alerts = {
                "performance_alerts": [],
                "quality_alerts": [],
                "opportunity_alerts": [],
                "risk_indicators": [],
                "alert_count": 0,
                "primary_chart": None  # Always include this key for downstream compatibility
            }
            
            # 1. PERFORMANCE ANOMALY DETECTION (2024 vs 2023 full year comparison)
            performance_query = """
            WITH performance_comparison AS (
                SELECT 
                    salesman_name_e,
                    ROUND(SUM(CASE WHEN yy = 2024 THEN sales_value ELSE 0 END), 3) as sales_2024,
                    ROUND(SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END), 3) as sales_2023,
                    COUNT(CASE WHEN yy = 2024 THEN 1 END) as transactions_2024
                FROM sales_data 
                WHERE yy IN (2023, 2024)
                GROUP BY salesman_name_e
                HAVING SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END) > 10000
            )
            SELECT salesman_name_e, sales_2024, sales_2023,
                   ROUND(((sales_2024 - sales_2023) / NULLIF(sales_2023, 0)) * 100, 1) as performance_change
            FROM performance_comparison 
            WHERE sales_2024 < sales_2023 * 0.9
            ORDER BY performance_change ASC LIMIT 3
            """
            
            result = conn.execute(text(performance_query)).fetchall()
            for row in result:
                alerts["performance_alerts"].append(
                    f"🔴 PERFORMANCE ALERT: {row[0]} sales dropped {abs(row[3])}% in 2024 vs 2023"
                )
                alerts["alert_count"] += 1
            
            # 2. RECENT TRENDS (2025 YTD vs same period 2024)
            recent_trends_query = """
            WITH recent_comparison AS (
                SELECT 
                    salesman_name_e,
                    ROUND(SUM(CASE WHEN yy = 2025 THEN sales_value ELSE 0 END), 3) as sales_2025_ytd,
                    ROUND(SUM(CASE WHEN yy = 2024 AND mm <= 5 THEN sales_value ELSE 0 END), 3) as sales_2024_same_period
                FROM sales_data 
                WHERE (yy = 2025) OR (yy = 2024 AND mm <= 5)
                GROUP BY salesman_name_e
                HAVING SUM(CASE WHEN yy = 2024 AND mm <= 5 THEN sales_value ELSE 0 END) > 5000
            )
            SELECT salesman_name_e, sales_2025_ytd, sales_2024_same_period,
                   ROUND(((sales_2025_ytd - sales_2024_same_period) / NULLIF(sales_2024_same_period, 0)) * 100, 1) as recent_change
            FROM recent_comparison 
            WHERE sales_2025_ytd < sales_2024_same_period * 0.9
            ORDER BY recent_change ASC LIMIT 2
            """
            
            result = conn.execute(text(recent_trends_query)).fetchall()
            for row in result:
                alerts["performance_alerts"].append(
                    f"🔴 RECENT TREND ALERT: {row[0]} down {abs(row[3])}% in 2025 YTD vs same period 2024"
                )
                alerts["alert_count"] += 1
            
            # 3. QUALITY/RETURN RATE ALERTS (2024 high return products)
            quality_query = """
            SELECT 
                item_name_e,
                ROUND(SUM(CASE WHEN tran_type = 'Sales' THEN sales_value ELSE 0 END), 3) as gross_sales,
                ROUND(SUM(CASE WHEN tran_type = 'Sales Return' THEN ABS(sales_value) ELSE 0 END), 3) as return_value,
                ROUND((SUM(CASE WHEN tran_type = 'Sales Return' THEN ABS(sales_value) ELSE 0 END) / 
                       NULLIF(SUM(CASE WHEN tran_type = 'Sales' THEN sales_value ELSE 0 END), 0)) * 100, 1) as return_rate
            FROM sales_data 
            WHERE yy = 2024
            GROUP BY item_name_e
            HAVING SUM(CASE WHEN tran_type = 'Sales' THEN sales_value ELSE 0 END) > 5000
               AND (SUM(CASE WHEN tran_type = 'Sales Return' THEN ABS(sales_value) ELSE 0 END) / 
                    NULLIF(SUM(CASE WHEN tran_type = 'Sales' THEN sales_value ELSE 0 END), 0)) * 100 > 8
            ORDER BY return_rate DESC LIMIT 3
            """
            
            result = conn.execute(text(quality_query)).fetchall()
            for row in result:
                alerts["quality_alerts"].append(
                    f"🟡 QUALITY ALERT: {row[0]} has {row[3]}% return rate in 2024 (>8% threshold)"
                )
                alerts["alert_count"] += 1
            
            # 4. GROWTH OPPORTUNITY DETECTION (Customers growing in 2025)
            opportunity_query = """
            WITH customer_growth AS (
                SELECT 
                    customer_name_e,
                    ROUND(SUM(CASE WHEN yy = 2025 THEN sales_value ELSE 0 END), 3) as sales_2025_ytd,
                    ROUND(SUM(CASE WHEN yy = 2024 AND mm <= 5 THEN sales_value ELSE 0 END), 3) as sales_2024_same_period
                FROM sales_data 
                WHERE (yy = 2025) OR (yy = 2024 AND mm <= 5)
                GROUP BY customer_name_e
                HAVING SUM(CASE WHEN yy = 2024 AND mm <= 5 THEN sales_value ELSE 0 END) > 5000 
                   AND SUM(CASE WHEN yy = 2025 THEN sales_value ELSE 0 END) > 
                       SUM(CASE WHEN yy = 2024 AND mm <= 5 THEN sales_value ELSE 0 END) * 1.5
            )
            SELECT customer_name_e, sales_2025_ytd, sales_2024_same_period,
                   ROUND(((sales_2025_ytd - sales_2024_same_period) / NULLIF(sales_2024_same_period, 0)) * 100, 1) as growth_rate
            FROM customer_growth
            ORDER BY growth_rate DESC LIMIT 2
            """
            
            result = conn.execute(text(opportunity_query)).fetchall()
            for row in result:
                alerts["opportunity_alerts"].append(
                    f"🟢 GROWTH OPPORTUNITY: {row[0]} up {row[3]:.1f}% in 2025 YTD - high upselling potential"
                )
                alerts["alert_count"] += 1
            
            # 5. BUSINESS RISK INDICATORS (Customers declining significantly)
            risk_query = """
            WITH customer_decline AS (
                SELECT 
                    customer_name_e,
                    SUM(CASE WHEN yy = 2024 THEN sales_value ELSE 0 END) as sales_2024,
                    SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END) as sales_2023
                FROM sales_data 
                WHERE yy IN (2023, 2024)
                GROUP BY customer_name_e
                HAVING SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END) > 15000
                   AND SUM(CASE WHEN yy = 2024 THEN sales_value ELSE 0 END) < 
                       SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END) * 0.5
            )
            SELECT COUNT(*) as declining_customers
            FROM customer_decline
            """
            
            result = conn.execute(text(risk_query)).fetchone()
            if result and result[0] > 0:
                alerts["risk_indicators"].append(
                    f"⚠️ RETENTION RISK: {result[0]} high-value customers declined 50%+ in 2024 vs 2023"
                )
                alerts["alert_count"] += 1
            
            return alerts
            
    except Exception as e:
        print(f"Error getting business intelligence alerts: {e}")
        return {
            "performance_alerts": [],
            "quality_alerts": [],
            "opportunity_alerts": [],
            "risk_indicators": [],
            "alert_count": 0,
            "primary_chart": None
        }

def build_modular_prompt(user_input: str, conversation_history: list = None) -> str:
    """Build a focused, modular prompt for faster processing"""
    
    # Get intent analysis for module selection (don't pass conversation_history to avoid dict issues)
    intent_analysis = get_advanced_intent_analysis(user_input, None)
    
    # Load the original system prompt (preserving all content)
    modular_prompt = get_relevant_prompt_sections(user_input, intent_analysis, conversation_history)
    
    # Add minimal conversation context for follow-ups only - handle different formats safely
    if conversation_history and len(conversation_history) > 0:
        try:
            context_items = []
            for item in conversation_history[-2:]:  # Only last 2 messages
                if isinstance(item, dict):
                    # Handle dict format (e.g., {"sender": "user", "content": "..."})
                    content = item.get('content', str(item))
                    sender = item.get('sender', 'unknown')
                    context_items.append(f"{sender}: {content}")
                elif isinstance(item, str):
                    # Handle string format
                    context_items.append(item)
                else:
                    # Handle other formats
                    context_items.append(str(item))
            
            if context_items:
                recent_context = "\n".join(context_items)
                modular_prompt += f"\n\n**RECENT CONTEXT:** {recent_context}"
        except Exception as e:
            print(f"[MODULAR PROMPT] Context processing error: {e}")
            # Skip context if there's an issue
            pass
    
    print(f"[MODULAR PROMPT] Selected modules for: '{user_input}'")
    print(f"[MODULAR PROMPT] Prompt size: {len(modular_prompt)} chars")
    
    return modular_prompt

def get_query_complexity_score(user_input: str) -> int:
    """Score query complexity to adjust response depth"""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
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

def get_advanced_intent_analysis(user_input: str, conversation_history: list = None) -> dict:
    """Advanced intent classification for complex user queries"""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
        
    intent_analysis = {
        "primary_intent": "general_inquiry",
        "complexity_level": 1,
        "business_scenario": "operational_analysis", 
        "requires_comparison": False,
        "requires_drill_down": False,
        "suggested_follow_ups": [],
        "confidence_score": 0.8
    }
    
    user_lower = user_input.lower()
    
    # Primary Intent Classification
    if any(word in user_lower for word in ["compare", "vs", "versus", "difference", "against"]):
        intent_analysis["primary_intent"] = "comparison"
        intent_analysis["requires_comparison"] = True
        intent_analysis["complexity_level"] = 3
    elif any(word in user_lower for word in ["trend", "over time", "growth", "decline", "pattern"]):
        intent_analysis["primary_intent"] = "trend_analysis"
        intent_analysis["complexity_level"] = 3
    elif any(word in user_lower for word in ["top", "best", "highest", "leading", "worst", "lowest"]):
        intent_analysis["primary_intent"] = "ranking"
        intent_analysis["complexity_level"] = 2
    elif any(word in user_lower for word in ["breakdown", "details", "drill down", "analyze", "deep dive"]):
        intent_analysis["primary_intent"] = "detailed_analysis"
        intent_analysis["requires_drill_down"] = True
        intent_analysis["complexity_level"] = 4
    elif any(word in user_lower for word in ["profit", "margin", "profitability", "roi"]):
        intent_analysis["primary_intent"] = "profitability"
        intent_analysis["complexity_level"] = 3
    elif any(word in user_lower for word in ["return", "refund", "quality", "issue"]):
        intent_analysis["primary_intent"] = "quality_analysis"
        intent_analysis["complexity_level"] = 3
    
    # Business Scenario Detection
    if any(word in user_lower for word in ["performance", "kpi", "target", "goal"]):
        intent_analysis["business_scenario"] = "performance_review"
    elif any(word in user_lower for word in ["forecast", "predict", "future", "plan"]):
        intent_analysis["business_scenario"] = "planning"
    elif any(word in user_lower for word in ["problem", "issue", "concern", "decline"]):
        intent_analysis["business_scenario"] = "troubleshooting"
    
    # Smart Follow-up Suggestions
    if intent_analysis["primary_intent"] == "ranking":
        intent_analysis["suggested_follow_ups"] = [
            "Would you like to see profit analysis for these top performers?",
            "Should I show their customer breakdown?", 
            "Want to compare with previous periods?"
        ]
    elif intent_analysis["primary_intent"] == "profitability":
        intent_analysis["suggested_follow_ups"] = [
            "Would you like to see cost breakdown analysis?",
            "Should I analyze return rates impact?",
            "Want to see margin trends over time?"
        ]
    
    return intent_analysis

def get_smart_query_clarification(user_input: str) -> dict:
    """Smart query clarification and auto-correction"""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
    clarification = {
        "needs_clarification": False,
        "auto_corrections": [],
        "suggestions": [],
        "ambiguity_score": 0.1
    }
    
    user_lower = user_input.lower()
    
    # Detect ambiguous terms
    if "performance" in user_lower and not any(entity in user_lower for entity in ["salesman", "customer", "product", "brand", "division"]):
        clarification["needs_clarification"] = True
        clarification["suggestions"] = [
            "Sales team performance",
            "Customer performance", 
            "Product performance",
            "Division performance"
        ]
    
    if "sales" in user_lower and "by" not in user_lower and not any(word in user_lower for word in ["total", "top", "best", "highest"]):
        clarification["needs_clarification"] = True
        clarification["suggestions"] = [
            "Total sales overview",
            "Sales by salesperson",
            "Sales by customer",
            "Sales by product",
            "Sales trends over time"
        ]
    
    # Auto-corrections for common mistakes
    corrections = {
        "salesman": "salesperson",
        "salesmen": "salespeople", 
        "employe": "employee",
        "costumer": "customer",
        "prodcut": "product",
        "prodict": "product",
        "divison": "division",
        "retur": "return",
        "profit margin": "profitability",
        "montly": "monthly",
        "yealy": "yearly"
    }
    
    for mistake, correction in corrections.items():
        if mistake in user_lower:
            clarification["auto_corrections"].append(mistake)
    
    return clarification

def get_temporal_intelligence(user_input: str) -> dict:
    """Advanced temporal intelligence for time-aware analytics"""
    
    # Handle different input types safely  
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
        
    temporal_context = {
        "time_scope": "current_period",
        "specific_periods": [],
        "growth_analysis": False,
        "seasonal_context": "standard",
        "forecast_horizon": None,
        "smart_suggestions": []
    }
    
    user_lower = user_input.lower()
    current_date = datetime.now()
    
    # Detect specific time periods (Database: 2023-2025, Latest: 2025-05)
    if any(phrase in user_lower for phrase in ["last quarter", "previous quarter", "q1"]):
        temporal_context["time_scope"] = "last_quarter"
        temporal_context["specific_periods"].append("Q1 2025 (Jan-Mar)")
        
    elif any(phrase in user_lower for phrase in ["this year", "2025", "current year"]):
        temporal_context["time_scope"] = "current_year"
        temporal_context["specific_periods"].append("2025")
        
    elif any(phrase in user_lower for phrase in ["last year", "2024", "previous year"]):
        temporal_context["time_scope"] = "previous_year" 
        temporal_context["specific_periods"].append("2024")
        
    elif any(phrase in user_lower for phrase in ["month", "monthly", "mtd"]):
        temporal_context["time_scope"] = "monthly"
        temporal_context["seasonal_context"] = True
        
    elif any(phrase in user_lower for phrase in ["ytd", "year to date"]):
        temporal_context["time_scope"] = "ytd"
        temporal_context["specific_periods"].append(f"YTD {current_date.year}")
    
    # Detect comparison intentions
    if any(phrase in user_lower for phrase in ["vs", "versus", "compare", "compared to", "against"]):
        temporal_context["comparison_periods"] = ["2023", "2024"]
        temporal_context["growth_analysis"] = True
        
    elif any(phrase in user_lower for phrase in ["growth", "increase", "decrease", "change", "trend"]):
        temporal_context["growth_analysis"] = True
        temporal_context["comparison_periods"] = ["Previous Period", "Current Period"]
    
    # Seasonal analysis detection
    if any(phrase in user_lower for phrase in ["seasonal", "quarter", "monthly", "seasonal patterns"]):
        temporal_context["seasonal_context"] = True
        temporal_context["smart_suggestions"].extend([
            "Consider analyzing quarterly patterns",
            "Review seasonal buying behavior",
            "Compare month-over-month trends"
        ])
    
    # Smart period suggestions
    if temporal_context["time_scope"] == "all_time":
        temporal_context["smart_suggestions"].extend([
            "Consider focusing on a specific time period for better insights",
            "You might want to compare recent periods",
            "Monthly or quarterly analysis often reveals patterns"
        ])
    
    return temporal_context

def get_smart_visualization_recommendations(user_input: str, query_context: dict = None, previous_viz_type: str = None) -> dict:
    """Smart Visualization AI - automatically recommends optimal chart types based on data and context
    Adds fallback and context preservation for format conversions."""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
    user_lower = user_input.lower()
    
    # Initialize recommendation engine
    viz_recommendations = {
        "primary_chart": "bar",
        "alternative_charts": [],
        "reasoning": "",
        "data_story": "",
        "interactive_elements": [],
        "color_psychology": "",
        "business_focus": ""
    }
    
    # 1. QUERY PATTERN ANALYSIS
    is_ranking = any(word in user_lower for word in ["top", "best", "highest", "leading", "worst", "lowest"])
    is_trend = any(word in user_lower for word in ["trend", "over time", "monthly", "yearly", "growth", "change"])
    is_comparison = any(word in user_lower for word in ["vs", "versus", "compare", "comparison", "between"])
    is_composition = any(word in user_lower for word in ["breakdown", "composition", "share", "percentage", "distribution"])
    is_relationship = any(word in user_lower for word in ["correlation", "relationship", "impact", "effect"])
    is_performance = any(word in user_lower for word in ["performance", "kpi", "target", "goal", "achievement"])
    
    # 🚀 NEW: CHART CONVERSION REQUEST DETECTION
    is_chart_conversion = any(phrase in user_lower for phrase in [
        "convert as a chart", "convert to chart", "show as chart", "make it a chart",
        "convert it as a chart", "turn into chart", "visualize this", "chart this"
    ])
    
    # 🔍 CONTEXT ANALYSIS: If this is a chart conversion, analyze conversation context
    if is_chart_conversion and query_context:
        print(f"[SMART VIZ AI] Chart conversion detected! Analyzing context...")
        
        # Try to extract context from previous queries/responses
        context_content = str(query_context)
        
        # Look for division/entity breakdown patterns in context
        if any(word in context_content.lower() for word in ["division", "department", "branch", "segment"]):
            is_composition = True
            detected_entity = "divisions"
            estimated_items = 7  # Based on your data showing 7 divisions
            print(f"[SMART VIZ AI] Context suggests division composition analysis")
            
        # Look for other composition patterns
        elif any(word in context_content.lower() for word in ["breakdown", "distribution", "share"]):
            is_composition = True
            print(f"[SMART VIZ AI] Context suggests composition analysis")
            
        # Look for ranking patterns  
        elif any(word in context_content.lower() for word in ["top", "best", "highest", "rank"]):
            is_ranking = True
            print(f"[SMART VIZ AI] Context suggests ranking analysis")
    
    # 2. ENTITY TYPE DETECTION
    entity_count_estimates = {
        "salespeople": 80,    # ~80 salespeople in dataset
        "customers": 200,     # ~200+ customers  
        "products": 1000,     # ~1000+ products
        "months": 12,         # 12 months max
        "quarters": 4,        # 4 quarters max
        "years": 3,           # 2023-2025
        "divisions": 10,      # ~10 divisions
        "brands": 50          # ~50 brands
    }
    
    detected_entity = "general"
    estimated_items = 10  # default
    
    for entity, count in entity_count_estimates.items():
        if any(term in user_lower for term in [entity, entity[:-1]]):  # singular/plural
            detected_entity = entity
            estimated_items = count
            break
    
    # 3. BUSINESS CONTEXT DETECTION
    is_executive_view = any(word in user_lower for word in ["overview", "summary", "executive", "dashboard"])
    is_detailed_analysis = any(word in user_lower for word in ["detailed", "comprehensive", "full", "complete"])
    is_operational = any(word in user_lower for word in ["daily", "weekly", "operational", "tactical"])
    is_strategic = any(word in user_lower for word in ["strategic", "planning", "forecast", "budget"])
    
    # 4. SMART CHART SELECTION ALGORITHM
    
    if is_trend and ("month" in user_lower or "time" in user_lower):
        # TIME SERIES DATA
        if is_comparison:
            viz_recommendations["primary_chart"] = "multi_line"
            viz_recommendations["reasoning"] = "Multi-line chart optimal for comparing trends over time"
            viz_recommendations["alternative_charts"] = ["line", "stacked_bar"]
        else:
            viz_recommendations["primary_chart"] = "line"
            viz_recommendations["reasoning"] = "Line chart best shows temporal patterns and trends"
            viz_recommendations["alternative_charts"] = ["bar", "multi_line"]
            
    elif is_ranking and estimated_items > 15:
        # LARGE RANKINGS
        viz_recommendations["primary_chart"] = "horizontal_bar"
        viz_recommendations["reasoning"] = "Horizontal bar chart handles many items with readable labels"
        viz_recommendations["alternative_charts"] = ["bar", "donut"]
        
    elif is_ranking and estimated_items <= 10:
        # SMALL RANKINGS  
        viz_recommendations["primary_chart"] = "bar"
        viz_recommendations["reasoning"] = "Vertical bar chart perfect for comparing top performers"
        viz_recommendations["alternative_charts"] = ["horizontal_bar", "donut"]
        
    elif is_composition or "share" in user_lower:
        # COMPOSITION ANALYSIS
        if estimated_items <= 8:
            viz_recommendations["primary_chart"] = "donut"
            viz_recommendations["reasoning"] = "Donut chart clearly shows proportional relationships"
            viz_recommendations["alternative_charts"] = ["bar", "horizontal_bar"]
        else:
            viz_recommendations["primary_chart"] = "stacked_bar"
            viz_recommendations["reasoning"] = "Stacked bar handles many categories better than pie charts"
            viz_recommendations["alternative_charts"] = ["bar", "horizontal_bar"]
            
    elif is_comparison and not is_trend:
        # STATIC COMPARISONS
        viz_recommendations["primary_chart"] = "stacked_bar"
        viz_recommendations["reasoning"] = "Stacked bar excellent for side-by-side comparisons"
        viz_recommendations["alternative_charts"] = ["bar", "horizontal_bar"]
        
    elif is_performance and any(word in user_lower for word in ["target", "goal", "achievement"]):
        # PERFORMANCE TRACKING
        viz_recommendations["primary_chart"] = "gauge"
        viz_recommendations["reasoning"] = "Gauge chart intuitive for performance vs target visualization"
        viz_recommendations["alternative_charts"] = ["bar", "horizontal_bar"]
        
    elif "waterfall" in user_lower or "breakdown" in user_lower:
        # BREAKDOWN ANALYSIS
        viz_recommendations["primary_chart"] = "waterfall"
        viz_recommendations["reasoning"] = "Waterfall chart shows step-by-step changes and contributions"
        viz_recommendations["alternative_charts"] = ["stacked_bar", "bar"]
        
    else:
        # DEFAULT INTELLIGENT SELECTION
        if estimated_items <= 5:
            viz_recommendations["primary_chart"] = "donut"
            viz_recommendations["reasoning"] = "Few items work well with donut for clear proportions"
        elif estimated_items <= 15:
            viz_recommendations["primary_chart"] = "bar"
            viz_recommendations["reasoning"] = "Medium dataset optimal for standard bar comparison"
        else:
            viz_recommendations["primary_chart"] = "horizontal_bar"
            viz_recommendations["reasoning"] = "Many items require horizontal layout for readability"
            
        viz_recommendations["alternative_charts"] = ["bar", "horizontal_bar", "donut"]
    
    # 5. COLOR PSYCHOLOGY SELECTION
    if "profit" in user_lower or "revenue" in user_lower:
        viz_recommendations["color_psychology"] = "success_green"
    elif "return" in user_lower or "loss" in user_lower:
        viz_recommendations["color_psychology"] = "warning_red"
    elif "performance" in user_lower:
        viz_recommendations["color_psychology"] = "professional_blue"
    elif is_trend:
        viz_recommendations["color_psychology"] = "gradient_blue"
    else:
        viz_recommendations["color_psychology"] = "corporate_palette"
    
    # 6. BUSINESS STORY GENERATION
    chart_benefits = {
        "bar": "Clear comparison of values, easy to read exact numbers",
        "horizontal_bar": "Perfect for long labels, handles many categories elegantly", 
        "line": "Shows trends and patterns over time, ideal for forecasting",
        "multi_line": "Compares multiple trends simultaneously, great for YoY analysis",
        "donut": "Emphasizes proportional relationships, intuitive for market share",
        "stacked_bar": "Shows both totals and component breakdowns",
        "waterfall": "Reveals how individual factors contribute to final result",
        "gauge": "Instantly communicates performance vs targets"
    }
    
    viz_recommendations["data_story"] = f"This {viz_recommendations['primary_chart']} visualization will {chart_benefits.get(viz_recommendations['primary_chart'], 'effectively display your data')}"
    
    # 7. INTERACTIVE ELEMENTS SUGGESTIONS
    if is_detailed_analysis:
        viz_recommendations["interactive_elements"] = ["drill_down", "hover_details", "zoom"]
    elif is_executive_view:
        viz_recommendations["interactive_elements"] = ["click_for_details", "summary_cards"]
    else:
        viz_recommendations["interactive_elements"] = ["hover_details"]
    
    # 8. BUSINESS FOCUS CONTEXT
    if is_strategic:
        viz_recommendations["business_focus"] = "strategic_overview"
    elif is_operational:
        viz_recommendations["business_focus"] = "operational_details"
    else:
        viz_recommendations["business_focus"] = "analytical_insights"
    
    # At the end, after all logic, add fallback/context preservation:
    recommended_chart_type = viz_recommendations["primary_chart"]
    if (not recommended_chart_type or recommended_chart_type not in ALLOWED_CHART_TYPES):
        if previous_viz_type in ALLOWED_CHART_TYPES:
            viz_recommendations["primary_chart"] = previous_viz_type
            viz_recommendations["reasoning"] += f" Previous chart type '{previous_viz_type}' reused for format conversion."
        else:
            viz_recommendations["primary_chart"] = "bar"
            viz_recommendations["reasoning"] += " No optimal chart type could be determined, so a standard bar chart is used."
    return viz_recommendations
