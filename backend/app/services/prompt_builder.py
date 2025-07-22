from app.core.db import engine
from sqlalchemy import text
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import re

# Allowed chart types for Smart Visualization AI
ALLOWED_CHART_TYPES = {"bar", "line", "donut", "horizontal_bar", "stacked_bar", "waterfall", "gauge", "multi_line"}

def get_smart_context(user_input: str) -> dict:
    """Generate smart context based on user query patterns"""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
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
                preview_blocks.append(f"**{table.upper()}:**\n{markdown_table}")
                
    except Exception as e:
        print(f"Error building prompt: {e}")
        table_names_str = "sales_data"
        preview_blocks = ["Error loading sample data"]
    
    preview_str = "\n".join(preview_blocks)
    
    # Add conversation history if provided
    history_context = ""
    if conversation_history and len(conversation_history) > 0:
        recent_messages = conversation_history[-5:]  # Last 5 messages for better context
        history_items = []
        entity_context = ""
        
        # Extract entity context from conversation
        last_bot_entity = None
        last_time_filter = None
        
        for msg in recent_messages:
            if msg.get('sender') == 'user':
                user_query = msg.get('content', '')
                
                # Handle different content types safely
                if isinstance(user_query, list):
                    user_query = " ".join(str(item) for item in user_query)
                elif not isinstance(user_query, str):
                    user_query = str(user_query)
                
                history_items.append(f"User Query: {user_query}")
                
                # Extract entity type from user query
                if any(term in user_query.lower() for term in ['salespeople', 'salesman', 'sales team']):
                    last_bot_entity = "salespeople"
                elif any(term in user_query.lower() for term in ['customer', 'client']):
                    last_bot_entity = "customers"
                elif any(term in user_query.lower() for term in ['product', 'item']):
                    last_bot_entity = "products"
                    
                # Extract time filter
                if '2024' in user_query:
                    last_time_filter = "WHERE yy = 2024"
                elif '2023' in user_query:
                    last_time_filter = "WHERE yy = 2023"
                    
            elif msg.get('sender') == 'bot':
                bot_response = msg.get('content', '')
                
                # Handle different content types safely - CRITICAL FIX
                if isinstance(bot_response, list):
                    # Extract text from response blocks
                    bot_response_text = ""
                    for block in bot_response:
                        if isinstance(block, dict):
                            if block.get('type') == 'text':
                                bot_response_text += block.get('template', '') + " " + block.get('text', '')
                            elif 'title' in block:
                                bot_response_text += block.get('title', '')
                    bot_response = bot_response_text
                elif not isinstance(bot_response, str):
                    bot_response = str(bot_response)
                
                # Try to extract entity context from bot response
                if 'top' in user_input.lower() and 'salespeople' in bot_response.lower():
                    last_bot_entity = "salespeople"
                elif 'customer' in bot_response.lower():
                    last_bot_entity = "customers"
                    
                history_items.append(f"Bot Response: {bot_response[:200]}...")
        
        if last_bot_entity:
            entity_context = f"\n🧠 CRITICAL CONVERSATION CONTEXT:\n- Last entity discussed: {last_bot_entity}\n- Time filter: {last_time_filter or 'All years'}\n- For follow-up queries, MAINTAIN this same entity context\n"
        
        history_context = f"""

CONVERSATION HISTORY (Last 5 messages):
{chr(10).join(history_items[-10:])}

{entity_context}

🚨 FOLLOW-UP INTELLIGENCE RULES:
- If user says "analyze their profit margins" → Apply to SAME entity set from previous query
- If user says "give me only top 5" → Use SAME entity type but LIMIT 5
- If user says "add profit analysis" → Add profit metrics to SAME entity context
- NEVER switch entity types unless explicitly requested
"""
    
    # Get all intelligence features
    intent_analysis = get_advanced_intent_analysis(user_input, conversation_history)
    clarification = get_smart_query_clarification(user_input)
    temporal_context = get_temporal_intelligence(user_input)
    business_insights = get_proactive_business_insights(user_input, temporal_context)
    business_alerts = get_real_time_business_alerts(user_input)  # Historical Business Intelligence
    viz_recommendations = get_smart_visualization_recommendations(user_input, context, business_alerts['primary_chart'])  # NEW: Smart Visualization AI

    # 🔍 DEBUG: Log what the Smart Visualization AI recommended
    print(f"[SMART VIZ AI] User Input: '{user_input}'")
    print(f"[SMART VIZ AI] Recommended Chart: '{viz_recommendations['primary_chart']}'")
    print(f"[SMART VIZ AI] Reasoning: '{viz_recommendations['reasoning']}'")
    print(f"[SMART VIZ AI] Context: {context}")

    # Build enhanced intelligence context
    intelligence_context = f"""
🧠 ADVANCED AI INTELLIGENCE ANALYSIS:

Intent Analysis:
- Primary Intent: {intent_analysis['primary_intent']}
- Complexity Level: {intent_analysis['complexity_level']}/4
- Business Scenario: {intent_analysis['business_scenario']}
- Requires Comparison: {intent_analysis['requires_comparison']}
- Requires Drill-down: {intent_analysis['requires_drill_down']}

Temporal Intelligence:
- Time Scope: {temporal_context['time_scope']}
- Specific Periods: {', '.join(temporal_context['specific_periods']) if temporal_context['specific_periods'] else 'All time'}
- Growth Analysis: {temporal_context['growth_analysis']}
- Seasonal Context: {temporal_context['seasonal_context']}

🎨 SMART VISUALIZATION AI RECOMMENDATIONS:
- Optimal Chart Type: {viz_recommendations['primary_chart']}
- Reasoning: {viz_recommendations['reasoning']}
- Alternative Charts: {', '.join(viz_recommendations['alternative_charts']) if viz_recommendations['alternative_charts'] else 'Standard options'}
- Data Story: {viz_recommendations['data_story']}
- Color Psychology: {viz_recommendations['color_psychology']}
- Business Focus: {viz_recommendations['business_focus']}
- Interactive Elements: {', '.join(viz_recommendations['interactive_elements']) if viz_recommendations['interactive_elements'] else 'Basic interaction'}

🚨 BUSINESS INTELLIGENCE ALERTS ({business_alerts['alert_count']} active):
Performance Alerts: {'; '.join(business_alerts['performance_alerts']) if business_alerts['performance_alerts'] else 'None'}
Quality Alerts: {'; '.join(business_alerts['quality_alerts']) if business_alerts['quality_alerts'] else 'None'}
Growth Opportunities: {'; '.join(business_alerts['opportunity_alerts']) if business_alerts['opportunity_alerts'] else 'None'}
Risk Indicators: {'; '.join(business_alerts['risk_indicators']) if business_alerts['risk_indicators'] else 'None'}

Query Clarification:
- Needs Clarification: {clarification['needs_clarification']}
- Auto-corrections: {clarification['auto_corrections'] if clarification['auto_corrections'] else 'None'}

Proactive Business Insights:
- Business Alerts: {'; '.join(business_insights['business_alerts']) if business_insights['business_alerts'] else 'None'}
- Optimization Suggestions: {'; '.join(business_insights['optimization_suggestions']) if business_insights['optimization_suggestions'] else 'None'}

Smart Follow-up Suggestions:
{chr(10).join(f"- {suggestion}" for suggestion in intent_analysis['suggested_follow_ups']) if intent_analysis['suggested_follow_ups'] else '- None'}

🎯 RESPONSE STRATEGY:
Based on this analysis, provide a {intent_analysis['complexity_level']}-level response with:
1. Strategic business context addressing the {intent_analysis['business_scenario']} scenario
2. Data analysis matching the {intent_analysis['primary_intent']} intent
3. {"Comparison analysis" if intent_analysis['requires_comparison'] else "Single-period analysis"}
4. {"Detailed drill-down capabilities" if intent_analysis['requires_drill_down'] else "High-level overview"}
5. Proactive suggestions for business optimization
6. Include relevant business intelligence alerts in the response context
7. Use the recommended chart type: {viz_recommendations['primary_chart']} for optimal data visualization
"""
    
    filled_prompt = base_prompt.replace("$table_names", table_names_str).replace("$sample_data", preview_str)
    
    return filled_prompt + history_context + intelligence_context

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
        "forecast_horizon": None
    }
    
    user_lower = user_input.lower()
    current_date = datetime.now()
    
    # Detect specific time periods
    if any(phrase in user_lower for phrase in ["last quarter", "previous quarter", "q4", "fourth quarter"]):
        temporal_context["time_scope"] = "last_quarter"
        temporal_context["specific_periods"].append("Q4 2024 (Oct-Dec)")
        
    elif any(phrase in user_lower for phrase in ["this year", "2024", "current year"]):
        temporal_context["time_scope"] = "current_year"
        temporal_context["specific_periods"].append("2024")
        
    elif any(phrase in user_lower for phrase in ["last year", "2023", "previous year"]):
        temporal_context["time_scope"] = "previous_year" 
        temporal_context["specific_periods"].append("2023")
        
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
