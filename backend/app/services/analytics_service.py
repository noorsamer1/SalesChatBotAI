import re
import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from ..models.models import UserAnalytics, PopularInsights, QueryCategories

class AnalyticsService:
    
    def __init__(self):
        self.query_categories = {
            "top_rankings": {
                "keywords": ["top", "best", "highest", "leading"],
                "entities": ["customer", "product", "salesperson", "division", "brand"],
                "icon": "🏆",
                "color": "#3B82F6",
                "description": "Top performer rankings and comparisons"
            },
            "sales_trends": {
                "keywords": ["trend", "over time", "monthly", "yearly", "seasonal"],
                "entities": ["sales", "revenue", "growth"],
                "icon": "📈",
                "color": "#10B981",
                "description": "Sales trends and time-series analysis"
            },
            "returns_analysis": {
                "keywords": ["return", "refund", "loss"],
                "entities": ["customer", "product", "quality"],
                "icon": "🔄",
                "color": "#F59E0B",
                "description": "Return patterns and quality analysis"
            },
            "profitability": {
                "keywords": ["profit", "margin", "profitable"],
                "entities": ["product", "customer", "division"],
                "icon": "💰",
                "color": "#8B5CF6",
                "description": "Profit analysis and margin insights"
            },
            "comparisons": {
                "keywords": ["compare", "vs", "versus", "difference"],
                "entities": ["year", "quarter", "division"],
                "icon": "⚖️",
                "color": "#EF4444",
                "description": "Performance comparisons and contrasts"
            },
            "growth_analysis": {
                "keywords": ["growth", "increase", "yoy", "expansion"],
                "entities": ["sales", "customer", "market"],
                "icon": "🚀",
                "color": "#06B6D4",
                "description": "Growth rates and expansion metrics"
            }
        }
    
    def categorize_query(self, query_text: str) -> Dict[str, any]:
        """Analyze query and categorize it"""
        query_lower = query_text.lower()
        
        # Extract entities
        entities = []
        entity_patterns = {
            "customers": ["customer", "client"],
            "products": ["product", "item"],
            "salespeople": ["salesperson", "sales rep", "sales team"],
            "divisions": ["division"],
            "brands": ["brand"],
            "managers": ["manager", "supervisor"],
            "returns": ["return", "refund"],
            "profit": ["profit", "margin"],
            "sales": ["sales", "revenue"]
        }
        
        for entity, keywords in entity_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                entities.append(entity)
        
        # Extract years
        years = re.findall(r'\b(20\d{2})\b', query_text)
        entities.extend(years)
        
        # Determine query category
        category = "general_analytics"
        category_score = 0
        
        for cat_name, cat_info in self.query_categories.items():
            score = 0
            # Check keywords
            for keyword in cat_info["keywords"]:
                if keyword in query_lower:
                    score += 2
            
            # Check entities
            for entity in cat_info["entities"]:
                if entity in query_lower:
                    score += 1
            
            if score > category_score:
                category_score = score
                category = cat_name
        
        # Determine query type
        query_type = "analysis"
        if any(word in query_lower for word in ["top", "best", "highest", "leading"]):
            query_type = "ranking"
        elif any(word in query_lower for word in ["trend", "over time", "monthly"]):
            query_type = "trend"
        elif any(word in query_lower for word in ["compare", "vs", "versus"]):
            query_type = "comparison"
        
        # Determine ideal chart type
        chart_type = "table"
        if query_type == "ranking":
            chart_type = "bar"
        elif query_type == "trend":
            chart_type = "line"
        elif "percentage" in query_lower or "composition" in query_lower:
            chart_type = "pie"
        
        return {
            "category": category,
            "query_type": query_type,
            "chart_type": chart_type,
            "entities": entities,
            "category_info": self.query_categories.get(category, {})
        }
    
    def track_query(self, db: Session, query_text: str, user_id: str, 
                   session_id: str, response_time_ms: int, success: bool = True,
                   error_message: str = None, response_content: str = None):
        """Track user query for analytics"""
        
        try:
            # Check if analytics tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            if 'user_analytics' not in inspector.get_table_names():
                print("Analytics tables not found. Skipping analytics tracking.")
                return
                
            analysis = self.categorize_query(query_text)
        except Exception as e:
            print(f"Analytics tracking failed: {e}")
            return
        
        # Create analytics record
        analytics_record = UserAnalytics(
            query_text=query_text,
            query_category=analysis["category"],
            query_type=analysis["query_type"],
            chart_type=analysis["chart_type"],
            entities_mentioned=analysis["entities"],
            response_time_ms=response_time_ms,
            user_id=user_id,
            session_id=session_id,
            success=success,
            error_message=error_message,
            response_length=len(response_content) if response_content else 0
        )
        
        db.add(analytics_record)
        
        # Update popular insights
        pattern = self._generate_query_pattern(query_text, analysis)
        popular_insight = db.query(PopularInsights).filter(
            PopularInsights.query_pattern == pattern
        ).first()
        
        if popular_insight:
            popular_insight.query_count += 1
            popular_insight.last_queried = datetime.utcnow()
            # Update average response time
            popular_insight.avg_response_time = (
                (popular_insight.avg_response_time * (popular_insight.query_count - 1) + response_time_ms) 
                / popular_insight.query_count
            )
        else:
            popular_insight = PopularInsights(
                query_pattern=pattern,
                query_count=1,
                avg_response_time=response_time_ms,
                category=analysis["category"],
                example_query=query_text
            )
            db.add(popular_insight)
        
        # Update category counts
        try:
            category = db.query(QueryCategories).filter(
                QueryCategories.category_name == analysis["category"]
            ).first()
            
            if category:
                category.query_count += 1
                category.updated_at = datetime.utcnow()
            else:
                category_info = analysis["category_info"]
                category = QueryCategories(
                    category_name=analysis["category"],
                    description=category_info.get("description", ""),
                    query_count=1,
                    icon=category_info.get("icon", "📊"),
                    color=category_info.get("color", "#6B7280")
                )
                db.add(category)
            
            db.commit()
        except Exception as e:
            print(f"Error in analytics tracking: {e}")
            db.rollback()
            raise
    
    def _generate_query_pattern(self, query_text: str, analysis: Dict) -> str:
        """Generate a pattern for the query"""
        query_lower = query_text.lower()
        
        # Replace specific values with placeholders
        pattern = query_lower
        
        # Replace years with {year}
        pattern = re.sub(r'\b20\d{2}\b', '{year}', pattern)
        
        # Replace numbers with {number}
        pattern = re.sub(r'\b\d+\b', '{number}', pattern)
        
        # Replace specific entity names with placeholders
        entity_replacements = {
            r'\b\w+\s+(customer|client)s?\b': '{customer}',
            r'\b\w+\s+(product|item)s?\b': '{product}',
            r'\b\w+\s+(division|department)s?\b': '{division}',
            r'\b\w+\s+(brand)s?\b': '{brand}'
        }
        
        for pattern_regex, replacement in entity_replacements.items():
            pattern = re.sub(pattern_regex, replacement, pattern)
        
        return pattern[:200]  # Limit length
    
    def get_dashboard_data(self, db: Session, days: int = 30) -> Dict:
        """Get analytics dashboard data"""
        
        try:
            # Check if analytics tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            if not all(table in tables for table in ['user_analytics', 'popular_insights', 'query_categories']):
                # Return empty/default data structure if tables don't exist
                return {
                    "summary": {
                        "total_queries": 0,
                        "success_rate": 0,
                        "avg_response_time": 0,
                        "active_days": 0
                    },
                    "daily_queries": [],
                    "popular_categories": [],
                    "popular_insights": [],
                    "query_types": [],
                    "chart_types": [],
                    "recent_queries": [],
                    "tables_missing": True,
                    "message": "Analytics tables not found. Please run create_analytics_tables.py to set up analytics tracking."
                }
        except Exception as e:
            print(f"Error checking analytics tables: {e}")
            return {
                "summary": {"total_queries": 0, "success_rate": 0, "avg_response_time": 0, "active_days": 0},
                "daily_queries": [], "popular_categories": [], "popular_insights": [],
                "query_types": [], "chart_types": [], "recent_queries": [],
                "error": f"Analytics check failed: {str(e)}"
            }
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Query volume over time
            daily_queries = db.query(
                func.date(UserAnalytics.timestamp).label('date'),
                func.count(UserAnalytics.id).label('query_count'),
                func.avg(UserAnalytics.response_time_ms).label('avg_response_time')
            ).filter(
                UserAnalytics.timestamp >= start_date
            ).group_by(
                func.date(UserAnalytics.timestamp)
            ).order_by('date').all()
            
            # Popular categories
            popular_categories = db.query(
                QueryCategories.category_name,
                QueryCategories.query_count,
                QueryCategories.icon,
                QueryCategories.color,
                QueryCategories.description
            ).order_by(desc(QueryCategories.query_count)).limit(10).all()
            
            # Popular insights
            popular_insights = db.query(PopularInsights).order_by(
                desc(PopularInsights.query_count)
            ).limit(15).all()
            
            # Query types distribution
            query_types = db.query(
                UserAnalytics.query_type,
                func.count(UserAnalytics.id).label('count')
            ).filter(
                UserAnalytics.timestamp >= start_date
            ).group_by(UserAnalytics.query_type).all()
            
            # Chart types usage
            chart_types = db.query(
                UserAnalytics.chart_type,
                func.count(UserAnalytics.id).label('count')
            ).filter(
                UserAnalytics.timestamp >= start_date
            ).group_by(UserAnalytics.chart_type).all()
            
            # Success rate
            # Count successful queries
            successful_count = db.query(func.count(UserAnalytics.id)).filter(
                UserAnalytics.timestamp >= start_date,
                UserAnalytics.success == True
            ).scalar() or 0
            
            # Count total queries
            total_count = db.query(func.count(UserAnalytics.id)).filter(
                UserAnalytics.timestamp >= start_date
            ).scalar() or 0
            
            # Create success stats object
            class SuccessStats:
                def __init__(self, successful, total):
                    self.successful = successful
                    self.total = total
            
            success_stats = SuccessStats(successful_count, total_count)
            
            success_rate = ((success_stats.successful or 0) / (success_stats.total or 1) * 100) if (success_stats.total or 0) > 0 else 0
            
            # Recent queries
            recent_queries = db.query(UserAnalytics).filter(
                UserAnalytics.timestamp >= start_date
            ).order_by(desc(UserAnalytics.timestamp)).limit(20).all()
            
            return {
                "summary": {
                    "total_queries": success_stats.total or 0,
                    "success_rate": round(success_rate, 1),
                    "avg_response_time": round(sum(q.avg_response_time or 0 for q in daily_queries) / len(daily_queries), 0) if daily_queries else 0,
                    "active_days": len(daily_queries)
                },
                "daily_queries": [
                    {
                        "date": q.date.strftime("%Y-%m-%d"),
                        "query_count": q.query_count or 0,
                        "avg_response_time": round(q.avg_response_time or 0, 0)
                    }
                    for q in daily_queries
                ],
                "popular_categories": [
                    {
                        "name": cat.category_name,
                        "count": cat.query_count,
                        "icon": cat.icon,
                        "color": cat.color,
                        "description": cat.description
                    }
                    for cat in popular_categories
                ],
                "popular_insights": [
                    {
                        "pattern": insight.query_pattern or "Unknown",
                        "count": insight.query_count or 0,
                        "category": insight.category or "General",
                        "example": insight.example_query or "No example available",
                        "avg_time": round(insight.avg_response_time or 0, 0)
                    }
                    for insight in popular_insights
                ],
                "query_types": [
                    {"type": qt.query_type, "count": qt.count}
                    for qt in query_types
                ],
                "chart_types": [
                    {"type": ct.chart_type, "count": ct.count}
                    for ct in chart_types
                ],
                "recent_queries": [
                    {
                        "query": (rq.query_text[:100] + "..." if rq.query_text and len(rq.query_text) > 100 else rq.query_text) or "No query text",
                        "category": rq.query_category or "General",
                        "timestamp": rq.timestamp.strftime("%Y-%m-%d %H:%M") if rq.timestamp else "Unknown",
                        "response_time": rq.response_time_ms or 0,
                        "success": rq.success or False
                    }
                    for rq in recent_queries
                ]
            }
        
        except Exception as e:
            print(f"Error in get_dashboard_data: {e}")
            return {
                "summary": {"total_queries": 0, "success_rate": 0, "avg_response_time": 0, "active_days": 0},
                "daily_queries": [], "popular_categories": [], "popular_insights": [],
                "query_types": [], "chart_types": [], "recent_queries": [],
                "error": f"Dashboard data fetch failed: {str(e)}"
            } 