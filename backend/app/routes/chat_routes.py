from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.db import get_db
from app.services.deps import get_current_user
from app.models.models import Conversation, Message
from app.services.openai_service import get_openai_response
from app.services.response_parser import parse_reply
import json
from app.services.table_utils import auto_pivot_llm_table, add_year_totals
from decimal import Decimal
import logging
import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

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

        # --- Start Robust NO DATA Logic Here ---
        # Define your no-data message (use same string as your fallback in your LLM output)
        NO_DATA_MESSAGE = "No sales/profit data found for last month. Please check another time period"
        # (Or whatever message you return for empty tables)

        # 1. Check for table/chart blocks with no data, and insert NO_DATA_MESSAGE if so
        def is_no_data_table(block):
            # Heuristic: Empty rows or all empty values
            if block.get("type") in ["table", "chart"]:
                rows = block.get("rows", [])
                if not rows or all(all((cell == "" or cell is None or cell == 0) for cell in row[1:]) for row in rows):
                    return True
            return False

        # 2. Remove adjacent summary text for empty results
        if isinstance(clean_reply, list):
            new_reply = []
            skip_next = False
            for idx, block in enumerate(clean_reply):
                # If this block is a table/chart and empty, and previous is a text summary, skip previous
                if is_no_data_table(block):
                    # Insert a NO_DATA_MESSAGE block and skip this table
                    if idx > 0 and clean_reply[idx-1].get("type") == "text":
                        new_reply = new_reply[:-1]  # Remove previous text block
                    new_reply.append({
                        "type": "text",
                        "template": NO_DATA_MESSAGE,
                        "value_code": ""
                    })
                    skip_next = True  # Skip the empty table
                elif skip_next:
                    skip_next = False
                else:
                    new_reply.append(block)
            # Only keep the first no-data block if multiples
            seen = set()
            final_reply = []
            for block in new_reply:
                if block["type"] == "text" and block["template"] == NO_DATA_MESSAGE:
                    if NO_DATA_MESSAGE in seen:
                        continue
                    seen.add(NO_DATA_MESSAGE)
                final_reply.append(block)
            clean_reply = final_reply

        elif isinstance(clean_reply, dict) and is_no_data_table(clean_reply):
            clean_reply = [{
                "type": "text",
                "template": NO_DATA_MESSAGE,
                "value_code": ""
            }]
        # --- End Robust NO DATA Logic ---

        # Hide zeros/nulls in all tables (if any left)
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