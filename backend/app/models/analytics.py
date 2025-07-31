from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Float
from datetime import datetime, timezone
from . import Base

class UserAnalytics(Base):
    __tablename__ = "user_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    query_category = Column(String(100))  # e.g., "top_customers", "sales_trends", "returns_analysis"
    query_type = Column(String(50))  # e.g., "ranking", "trend", "comparison"
    chart_type = Column(String(20))  # "bar", "line", "pie", "table"
    entities_mentioned = Column(JSON)  # ["customers", "products", "2024"]
    response_time_ms = Column(Integer)
    user_id = Column(String(100))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session_id = Column(String(100))
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Usage metrics
    execution_time_ms = Column(Integer)
    response_length = Column(Integer)  # Length of response content
    
class PopularInsights(Base):
    __tablename__ = "popular_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    query_pattern = Column(String(200), unique=True)  # Pattern like "top_{entity}_by_{metric}"
    query_count = Column(Integer, default=1)
    last_queried = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    avg_response_time = Column(Float)
    category = Column(String(50))
    example_query = Column(Text)
    
class QueryCategories(Base):
    __tablename__ = "query_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), unique=True)
    description = Column(Text)
    query_count = Column(Integer, default=0)
    icon = Column(String(10))  # Emoji icon
    color = Column(String(7))  # Hex color code
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))