# app/models.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender = Column(String)  # "user" or "bot"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


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
    timestamp = Column(DateTime, default=datetime.utcnow)
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
    last_queried = Column(DateTime, default=datetime.utcnow)
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
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
