from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.analytics_service import AnalyticsService
from app.services.deps import get_current_user

analytics_routes = APIRouter(prefix="/analytics", tags=["Analytics"])
analytics_service = AnalyticsService()

@analytics_routes.get("/dashboard")
async def get_analytics_dashboard(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get analytics dashboard data showing user query patterns and popular insights"""
    try:
        dashboard_data = analytics_service.get_dashboard_data(db, days)
        return {
            "success": True,
            "data": dashboard_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")

@analytics_routes.get("/query-patterns")
async def get_query_patterns(
    category: str = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get popular query patterns by category"""
    try:
        from sqlalchemy import desc
        from app.models.analytics import PopularInsights
        
        query = db.query(PopularInsights)
        
        if category:
            query = query.filter(PopularInsights.category == category)
        
        insights = query.order_by(desc(PopularInsights.query_count)).limit(limit).all()
        
        return {
            "success": True,
            "patterns": [
                {
                    "pattern": insight.query_pattern,
                    "count": insight.query_count,
                    "category": insight.category,
                    "example": insight.example_query,
                    "avg_response_time": insight.avg_response_time,
                    "last_queried": insight.last_queried.strftime("%Y-%m-%d %H:%M")
                }
                for insight in insights
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching query patterns: {str(e)}")

@analytics_routes.get("/categories")
async def get_query_categories(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get all query categories with usage statistics"""
    try:
        from sqlalchemy import desc
        from app.models.analytics import QueryCategories
        
        categories = db.query(QueryCategories).order_by(desc(QueryCategories.query_count)).all()
        
        return {
            "success": True,
            "categories": [
                {
                    "name": cat.category_name,
                    "description": cat.description,
                    "count": cat.query_count,
                    "icon": cat.icon,
                    "color": cat.color,
                    "last_updated": cat.updated_at.strftime("%Y-%m-%d")
                }
                for cat in categories
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")

@analytics_routes.post("/track")
async def track_query_analytics(
    query_data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Track a query for analytics (called internally by chat system)"""
    try:
        analytics_service.track_query(
            db=db,
            query_text=query_data.get("query"),
            user_id=current_user.get("id", "anonymous"),
            session_id=query_data.get("session_id", ""),
            response_time_ms=query_data.get("response_time", 0),
            success=query_data.get("success", True),
            error_message=query_data.get("error"),
            response_content=query_data.get("response_content", "")
        )
        
        return {"success": True, "message": "Query tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking query: {str(e)}")

@analytics_routes.get("/suggestions")
async def get_query_suggestions(
    user_history: bool = True,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get intelligent query suggestions based on patterns and user history"""
    try:
        from sqlalchemy import desc, func
        from app.models.analytics import PopularInsights, UserAnalytics
        
        suggestions = []
        
        if user_history:
            # Get user's most common query categories
            user_categories = db.query(
                UserAnalytics.query_category,
                func.count(UserAnalytics.id).label('count')
            ).filter(
                UserAnalytics.user_id == current_user.get("id", "anonymous")
            ).group_by(
                UserAnalytics.query_category
            ).order_by(desc('count')).limit(3).all()
            
            for cat in user_categories:
                # Get popular queries in this category
                category_suggestions = db.query(PopularInsights).filter(
                    PopularInsights.category == cat.query_category
                ).order_by(desc(PopularInsights.query_count)).limit(3).all()
                
                suggestions.extend([
                    {
                        "query": insight.example_query,
                        "category": insight.category,
                        "popularity": insight.query_count,
                        "source": "user_preference"
                    }
                    for insight in category_suggestions
                ])
        
        # Add globally popular queries
        global_popular = db.query(PopularInsights).order_by(
            desc(PopularInsights.query_count)
        ).limit(limit - len(suggestions)).all()
        
        suggestions.extend([
            {
                "query": insight.example_query,
                "category": insight.category,
                "popularity": insight.query_count,
                "source": "trending"
            }
            for insight in global_popular
        ])
        
        return {
            "success": True,
            "suggestions": suggestions[:limit]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting suggestions: {str(e)}") 