from sqlalchemy.orm import declarative_base
Base = declarative_base()

from .auth import User
from .chat import Conversation, Message
from .analytics import UserAnalytics, PopularInsights, QueryCategories

# Export all models
__all__ = [
    'Base',
    'User',
    'Conversation',
    'Message',
    'UserAnalytics',
    'PopularInsights',
    'QueryCategories'
]