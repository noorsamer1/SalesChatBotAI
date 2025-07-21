#!/usr/bin/env python3
"""
Create analytics tables for user query tracking
Run this once to set up the analytics database tables
"""

from app.core.db import engine
from app.models.models import Base

def create_analytics_tables():
    """Create analytics tables in the database"""
    try:
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        print("✅ Analytics tables created successfully!")
        print("Created tables:")
        print("  - user_analytics (query tracking)")
        print("  - popular_insights (trending queries)")
        print("  - query_categories (category statistics)")
        
    except Exception as e:
        print(f"❌ Error creating analytics tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Creating analytics tables...")
    success = create_analytics_tables()
    
    if success:
        print("\n🎉 Analytics database setup complete!")
        print("Your chatbot can now track:")
        print("  📊 User query patterns")
        print("  🔥 Popular insights")
        print("  📈 Usage statistics")
        print("  ⚡ Performance metrics")
    else:
        print("\n💥 Setup failed. Please check your database connection.") 