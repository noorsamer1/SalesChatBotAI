from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.db import get_db
from app.services.deps import get_current_user
from app.models.models import Conversation, Message
from app.services.openai_service import get_openai_response
from app.services.response_parser import parse_reply
from app.services.analytics_service import AnalyticsService
import json
from app.services.table_utils import auto_pivot_llm_table, add_year_totals
from decimal import Decimal
import logging
import datetime
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
analytics_service = AnalyticsService()

def hide_zero_null(table_block):
    """Hide zero and null values in table displays"""
    for row in table_block['rows']:
        for i in range(1, len(row)):
            if row[i] is None or (isinstance(row[i], (int, float)) and row[i] == 0):
                row[i] = ""
    return table_block

def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

def get_conversation_history(conversation_id: int, db: Session, limit: int = 10) -> list:
    """Get recent conversation history for context"""
    try:
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.desc()).limit(limit).all()
        
        # Reverse to get chronological order
        messages.reverse()
        
        history = []
        for msg in messages:
            content = msg.content
            if msg.sender == "bot" and isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    content = content
            
            history.append({
                "sender": msg.sender,
                "content": content,
                "timestamp": msg.timestamp
            })
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return []

def generate_smart_title(user_input: str) -> str:
    """Generate smart conversation titles based on user input"""
    input_lower = user_input.lower()
    
    # Common patterns for sales queries
    if any(word in input_lower for word in ["top", "best", "highest"]):
        if "customer" in input_lower:
            return "Top Customers Analysis"
        elif "product" in input_lower:
            return "Top Products Analysis"
        elif "sales" in input_lower:
            return "Top Sales Performance"
    
    if any(word in input_lower for word in ["trend", "over time", "monthly", "yearly"]):
        return "Sales Trend Analysis"
    
    if any(word in input_lower for word in ["return", "refund"]):
        return "Returns Analysis"
    
    if any(word in input_lower for word in ["profit", "margin"]):
        return "Profitability Analysis"
    
    if any(word in input_lower for word in ["comparison", "compare", "vs"]):
        return "Comparative Analysis"
    
    # Default based on first few words
    words = user_input.split()[:3]
    return " ".join(words).title() if words else "Sales Query"

class ConversationCreate(BaseModel):
    title: str = "New Chat"

class MessageCreate(BaseModel):
    content: str

@router.post("/conversations", response_model=dict)
def create_conversation(conv: ConversationCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Create a new conversation"""
    try:
        new_conv = Conversation(user_id=user.id, title=conv.title)
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        
        logger.info(f"Created new conversation {new_conv.id} for user {user.id}")
        return {"id": new_conv.id, "title": new_conv.title}
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create conversation")

@router.get("/conversations", response_model=list)
def list_conversations(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """List all conversations for the current user"""
    try:
        convs = db.query(Conversation).filter(
            Conversation.user_id == user.id
        ).order_by(Conversation.created_at.desc()).all()
        
        logger.info(f"Retrieved {len(convs)} conversations for user {user.id}")
        return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in convs]
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")

@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Delete a conversation and all its messages"""
    try:
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id, 
            Conversation.user_id == user.id
        ).first()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete all messages first
        db.query(Message).filter(Message.conversation_id == conv_id).delete()
        
        # Delete the conversation
        db.delete(conv)
        db.commit()
        
        logger.info(f"Deleted conversation {conv_id} for user {user.id}")
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

@router.get("/conversations/{conv_id}/messages", response_model=list)
def get_messages(conv_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Get all messages in a conversation"""
    try:
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id, 
            Conversation.user_id == user.id
        ).first()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = []
        for m in conv.messages:
            content = m.content
            
            # Parse bot messages
            if m.sender == "bot" and isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    content = [{"type": "text", "text": content}]
            
            messages.append({
                "id": m.id,
                "sender": m.sender,
                "content": content,
                "timestamp": m.timestamp
            })
        
        logger.info(f"Retrieved {len(messages)} messages for conversation {conv_id}")
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")

@router.post("/conversations/{conv_id}/messages", response_model=dict)
def send_message(conv_id: int, msg: MessageCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Send a message and get AI response"""
    start_time = time.time()
    try:
        # Validate conversation exists and belongs to user
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id, 
            Conversation.user_id == user.id
        ).first()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Save user message
        user_msg = Message(conversation_id=conv_id, sender="user", content=msg.content)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        
        # Get conversation history for context
        history = get_conversation_history(conv_id, db, limit=5)
        
        # Generate AI response with context
        raw_response = get_openai_response(msg.content, history)
        bot_reply = parse_reply(raw_response)
        clean_reply = convert_decimals(bot_reply)

        # Hide zero/null values in tables
        def hide_zero_null(table_block):
            for row in table_block['rows']:
                for i in range(1, len(row)):
                    if row[i] is None or (isinstance(row[i], (int, float)) and row[i] == 0):
                        row[i] = ""
            return table_block

        # --- FIXED NO DATA Logic - Don't replace charts with data ---
        NO_DATA_MESSAGE = "No data found for your query. Please try a different time period or criteria."

        def has_valid_data(block):
            """Check if a block has valid data"""
            block_type = block.get("type")
            logger.debug(f"Validating block type: {block_type}")
            
            if block.get("type") == "chart":
                chart_data = block.get("chart_data", {})
                labels = chart_data.get("labels", [])
                
                # 🚀 ENHANCED: Handle all chart formats (single, multi-series, professional charts)
                if chart_data.get("multi_series"):
                    has_labels = len(labels) > 0
                    
                    # Check for new multi-series format (stacked_bar, multi_line, etc.)
                    values_data = chart_data.get("values", {})
                    if isinstance(values_data, dict):
                        # New format: {"values": {"series1": [1,2,3], "series2": [4,5,6]}}
                        has_series_data = any(
                            len(series_values) > 0 and any(v != 0 for v in series_values if isinstance(v, (int, float)))
                            for series_values in values_data.values()
                        )
                        logger.debug(f"Multi-series chart validation (new format): labels={has_labels}, series_data={has_series_data}, series_count={len(values_data)}")
                        return has_labels and has_series_data
                    
                    # Check for old multi-series format
                    elif chart_data.get("series"):
                        # Old format: {"series": [{"values": [...]}, ...]}
                        series = chart_data.get("series", [])
                        has_series_data = len(series) > 0 and any(
                            len(s.get("values", [])) > 0 and any(v != 0 for v in s.get("values", []) if isinstance(v, (int, float)))
                            for s in series
                        )
                        logger.debug(f"Multi-series chart validation (old format): labels={has_labels}, series_data={has_series_data}")
                        return has_labels and has_series_data
                    
                    else:
                        logger.debug("Multi-series chart missing data structure")
                        return False
                else:
                    # Single-series chart validation (original logic + professional charts)
                    values = chart_data.get("values", [])
                    if isinstance(values, list):
                        # Standard single-series format
                        has_data = len(labels) > 0 and len(values) > 0 and any(v != 0 for v in values if isinstance(v, (int, float)))
                        logger.debug(f"Single-series chart validation: labels={len(labels)}, values={len(values)}, has_data={has_data}")
                        return has_data
                    else:
                        # Professional chart formats (gauge, heatmap) may have different structures
                        logger.debug(f"Professional chart validation: labels={len(labels)}, has_values={bool(values)}")
                        return len(labels) > 0 or bool(values)
            
            elif block.get("type") == "table":
                rows = block.get("rows", [])
                logger.debug(f"Table validation: {len(rows)} rows found")
                
                # Table has data if it has any rows with content
                if not rows:
                    logger.debug("Table validation: No rows found")
                    return False
                
                # Check if ANY row has meaningful content (don't be too strict about headers)
                has_content = any(
                    any(cell for cell in row if cell and str(cell).strip() != "" and str(cell).strip() != "0") 
                    for row in rows
                )
                logger.debug(f"Table validation: Has meaningful content = {has_content}")
                return has_content
            
            elif block.get("type") == "text":
                # Text blocks are always valid
                return True
            
            return True

        # Only replace with NO_DATA_MESSAGE if ALL data blocks are empty
        if isinstance(clean_reply, list):
            data_blocks = [block for block in clean_reply if block.get("type") in ["chart", "table"]]
            text_blocks = [block for block in clean_reply if block.get("type") == "text"]
            
            logger.debug(f"Data validation: Found {len(data_blocks)} data blocks, {len(text_blocks)} text blocks")
            
            # Check if we have data blocks and if ANY of them have valid data
            if data_blocks:
                validation_results = []
                for i, block in enumerate(data_blocks):
                    is_valid = has_valid_data(block)
                    validation_results.append(is_valid)
                    logger.debug(f"Block {i} (type: {block.get('type')}): Valid = {is_valid}")
                
                has_any_valid_data = any(validation_results)
                logger.debug(f"Final validation result: Has any valid data = {has_any_valid_data}")
                
                if not has_any_valid_data:
                    # Only then replace with no data message
                    logger.warning("All data blocks deemed invalid - replacing with no data message")
                    clean_reply = [{
                        "type": "text",
                        "template": NO_DATA_MESSAGE,
                        "value_code": ""
                    }]
                else:
                    # Keep all blocks with data, remove empty ones
                    logger.debug("Keeping valid data blocks, filtering out empty ones")
                    clean_reply = [
                        block for block in clean_reply 
                        if block.get("type") == "text" or has_valid_data(block)
                    ]

        # Hide zeros/nulls in remaining tables
        if isinstance(clean_reply, list):
            for i, block in enumerate(clean_reply):
                if isinstance(block, dict) and block.get("type") == "table":
                    try:
                        clean_reply[i] = hide_zero_null(block)
                    except Exception as e:
                        logger.error(f"Error processing table: {e}")
        elif isinstance(clean_reply, dict) and clean_reply.get("type") == "table":
            try:
                clean_reply = hide_zero_null(clean_reply)
            except Exception as e:
                logger.error(f"Error processing table: {e}")

        # Update conversation title if this is the first message
        if len(history) <= 1:  # Only user message exists
            smart_title = generate_smart_title(msg.content)
            conv.title = smart_title
            db.commit()
        
        # Save bot response
        bot_content = json.dumps(clean_reply)
        bot_msg = Message(conversation_id=conv_id, sender="bot", content=bot_content)
        db.add(bot_msg)
        db.commit()
        db.refresh(bot_msg)
        
        logger.info(f"Processed message in conversation {conv_id} - Generated {len(clean_reply) if isinstance(clean_reply, list) else 1} response blocks")
        
        # Track analytics (non-blocking)
        try:
            response_time_ms = int((time.time() - start_time) * 1000)
            analytics_service.track_query(
                db=db,
                query_text=msg.content,
                user_id=str(user.id),
                session_id=str(conv_id),
                response_time_ms=response_time_ms,
                success=True,
                response_content=json.dumps(clean_reply)
            )
            logger.info(f"Analytics tracked successfully for query: {msg.content[:50]}...")
        except Exception as analytics_error:
            logger.warning(f"Analytics tracking failed (non-critical): {analytics_error}")
            # Analytics failure should not block chat functionality
            pass
        
        return {
            "user_message": {
                "id": user_msg.id,
                "sender": user_msg.sender,
                "content": user_msg.content,
                "timestamp": user_msg.timestamp
            },
            "bot_message": {
                "id": bot_msg.id,
                "sender": bot_msg.sender,
                "content": clean_reply,
                "timestamp": bot_msg.timestamp
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        
        # Track failed analytics (non-blocking)
        try:
            response_time_ms = int((time.time() - start_time) * 1000)
            analytics_service.track_query(
                db=db,
                query_text=msg.content,
                user_id=str(user.id),
                session_id=str(conv_id),
                response_time_ms=response_time_ms,
                success=False,
                error_message=str(e)
            )
        except Exception as analytics_error:
            logger.warning(f"Analytics tracking failed (non-critical): {analytics_error}")
            # Don't let analytics failure mask the real error
            pass
        
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process message")
    
@router.get("/conversations/{conv_id}/export")
def export_conversation(conv_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Export conversation as JSON"""
    try:
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id, 
            Conversation.user_id == user.id
        ).first()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = get_messages(conv_id, db, user)
        
        export_data = {
            "conversation_id": conv_id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
            "user": user.username,
            "messages": messages,
            "export_timestamp": datetime.now().isoformat()
        }
        
        return export_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to export conversation")