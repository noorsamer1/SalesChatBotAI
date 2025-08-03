from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.db import get_db
from app.services.auth_deps import get_current_user
from app.models.chat import Conversation, Message
from app.services.openai_service import get_openai_response_fast, get_openai_response_stream_enhanced, enhance_sql_query, validate_response_structure
from app.services.response_parser import parse_reply
from app.services.analytics_service import AnalyticsService
import json
import logging
import datetime
import time
import asyncio
from typing import AsyncGenerator
from app.services.auth_utils import get_user_from_token
import re
from app.services.improved_json_parser import convert_decimals, parse_openai_response

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

def generate_llm_title(user_input: str) -> str:
    """Generate intelligent conversation titles using LLM"""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
    try:
        from app.services.openai_service import client
        
        title_prompt = f"""Generate a concise, professional conversation title (max 6 words) for this business analytics query:

Query: "{user_input}"

Rules:
- Focus on the main business entity (customers, products, sales, etc.)
- Include the analysis type (trends, performance, comparison, etc.)
- Keep it business-professional
- Maximum 6 words
- Examples:
  * "Top Customers Sales Analysis"
  * "Monthly Revenue Trends 2024"
  * "Division Performance Comparison"
  * "Product Returns Investigation"

Title:"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=20,
            temperature=0.3
        )
        
        title = response.choices[0].message.content.strip()
        
        # Clean up the title
        title = title.replace('"', '').replace("'", "").strip()
        
        # Fallback if title is too long or empty
        if len(title) > 50 or len(title) == 0:
            return generate_smart_title(user_input)
        
        return title
        
    except Exception as e:
        logger.error(f"LLM title generation failed: {e}")
        return generate_smart_title(user_input)

def generate_smart_title(user_input: str) -> str:
    """Generate smart conversation titles based on user input"""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
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
        
        # Delete all messages first to avoid foreign key constraint violation
        deleted_messages = db.query(Message).filter(Message.conversation_id == conv_id).delete()
        logger.info(f"Deleted {deleted_messages} messages for conversation {conv_id}")
        
        # Now delete the conversation
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
    """Send a message and get AI response (non-streaming) with year disambiguation and context inheritance"""
    start_time = time.time()
    try:
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id, 
            Conversation.user_id == user.id
        ).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Clear any orphaned pending questions that might cause issues
        if hasattr(conv, "pending_question") and conv.pending_question:
            # Check if the pending question is very old (more than 10 messages ago)
            recent_messages = db.query(Message).filter(
                Message.conversation_id == conv_id
            ).order_by(Message.timestamp.desc()).limit(10).all()
            
            # If we have recent messages, clear old pending questions
            if len(recent_messages) >= 5:
                logger.info(f"[CLEANUP] Clearing old pending question: {conv.pending_question}")
                conv.pending_question = None
                db.commit()

        # Save user message
        user_msg = Message(conversation_id=conv_id, sender="user", content=msg.content)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Clean user input for analysis
        user_input = msg.content.strip()
        user_input_lower = user_input.lower()
        
        # Detect greetings and non-analytics queries that should NOT trigger year clarification
        # Check for acknowledgment/continuation phrases FIRST
        acknowledgment_patterns = [
            r'^(okay|ok|yes|yep|yeah|sure|continue|go ahead|proceed)[\s\.,!]*$'
        ]
        is_acknowledgment = any(re.match(pattern, user_input_lower) for pattern in acknowledgment_patterns)
        
        # Check for incomplete previous response that needs completion
        needs_completion = False
        if is_acknowledgment:
            # Check if the last bot message was incomplete (only text, no data)
            history = get_conversation_history(conv_id, db, limit=2)
            if len(history) >= 2:
                last_bot_msg = history[-2]  # Previous bot message
                if last_bot_msg.get("sender") == "bot":
                    content = last_bot_msg.get("content", [])
                    if isinstance(content, list) and len(content) == 1:
                        if content[0].get("type") == "text" and "underperforming" in content[0].get("template", "").lower():
                            needs_completion = True
                            logger.info("[ACKNOWLEDGMENT] Detected need to complete underperforming SKUs query")
        
        greeting_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon|good evening|greetings)[\s\.,!]*$',
            r'^(how are you|what\'s up|how do you do)[\s\.,!]*$',
            r'^(thanks|thank you|thx)[\s\.,!]*$',
            r'^(bye|goodbye|see you|farewell)[\s\.,!]*$',
            r'^(help|what can you do|what do you do)[\s\.,!]*$',
            r'^(test|testing)[\s\.,!]*$',
            r'what.*servi.*provide',  # More flexible for typos (servies/services)
            r'what.*can.*you.*do',
            r'what.*do.*you.*offer',
            r'tell me about.*capabilit',
            r'how.*can.*you.*help'
        ]
        
        # Check if this is a greeting or general conversation (but not acknowledgment)
        is_greeting = any(re.match(pattern, user_input_lower) for pattern in greeting_patterns) and not needs_completion
        
        # Check if this is a format conversion request (should also skip year clarification)
        format_conversion_patterns = [
            "show as a bar chart", "show as a chart", "convert to chart", "show as table", 
            "table format", "chart view", "make it a table", "as a table", "as a chart", 
            "convert to table", "give it to me as a table", "display as table", 
            "display as chart", "chart please", "table please", "as a line chart",
            "as a bar chart", "as a donut chart", "as a pie chart", "show as line chart",
            "show as bar chart", "convert to line chart", "convert to bar chart",
            "make it a line chart", "make it a bar chart", "line chart", "bar chart"
        ]
        is_format_conversion = any(phrase in user_input_lower for phrase in format_conversion_patterns)
        
        # Robust year/period detection patterns
        year_match = re.search(r"\b(20\d{2})\b", user_input)
        multi_year_match = re.search(r"(20\d{2})\s*(?:-|to|and|vs)\s*(20\d{2})", user_input)
        all_years_match = re.search(r"all years|all time|entire period|overall|total", user_input)
        period_match = re.search(r"q[1-4]|quarter|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|month|week|day", user_input)
        
        # Check if this is a simple year reply (just a year, nothing else)
        is_simple_year = re.match(r"^\s*(in\s+)?(20\d{2})\s*$", user_input_lower)
        
        # Priority 1: Handle pending question + year reply
        if hasattr(conv, "pending_question") and conv.pending_question:
            logger.info(f"[PENDING QUESTION] Found: {conv.pending_question}")
            logger.info(f"[USER REPLY] {user_input}")
            
            # If user reply contains a year or is a simple year, combine with pending question
            if is_simple_year or year_match or multi_year_match or all_years_match or period_match:
                # Extract year from user input
                if is_simple_year:
                    year_part = is_simple_year.group(2)
                    final_query = f"{conv.pending_question.strip()} in {year_part}"
                elif all_years_match:
                    final_query = f"{conv.pending_question.strip()} for all years"
                elif multi_year_match:
                    final_query = f"{conv.pending_question.strip()} for {multi_year_match.group(0)}"
                elif year_match:
                    final_query = f"{conv.pending_question.strip()} in {year_match.group(0)}"
                else:
                    final_query = f"{conv.pending_question.strip()} {user_input}"
                
                user_input = final_query
                logger.info(f"[COMBINED QUERY] {user_input}")
                
                # Don't clear pending_question yet - wait until after successful LLM response
            else:
                # User replied with something that's not a year - treat as new question
                # Clear pending question and continue with regular flow
                conv.pending_question = None
                db.commit()
                user_input = msg.content.strip()
        
        # Priority 2: Check if current query has year/period info
        has_time_info = (year_match or multi_year_match or all_years_match or period_match)
        
        # Priority 3: If no time info and no pending question, check for context inheritance
        if not has_time_info and not (hasattr(conv, "pending_question") and conv.pending_question):
            # Handle greetings immediately without OpenAI calls
            if is_greeting:
                # Generate immediate greeting response
                if any(word in user_input_lower for word in ['help', 'what can you do', 'what do you do']):
                    bot_reply = [{
                        "type": "text",
                        "template": "I'm FutureTec, your specialized sales analytics AI assistant. I can help you with: 📊 Sales performance analysis, 🏆 Top customers/products/salespeople rankings, 📈 Revenue and profit trends, 🔄 Returns and quality analysis, 📅 Time-based comparisons (monthly, quarterly, yearly), 🎯 Customer segmentation, 📍 Geographic performance analysis. Just ask me any sales-related question and I'll provide detailed insights with data tables and charts!",
                        "value_code": ""
                    }]
                else:
                    bot_reply = [{
                        "type": "text", 
                        "template": "Hello! I'm FutureTec, your AI sales analytics assistant for Kuwait market data. I can help you analyze sales performance, customer insights, product trends, and business metrics. What would you like to explore today?",
                        "value_code": ""
                    }]
                
                # Save bot response immediately
                bot_content = json.dumps(bot_reply)
                bot_msg = Message(conversation_id=conv_id, sender="bot", content=bot_content)
                db.add(bot_msg)
                db.commit()
                db.refresh(bot_msg)
                
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
                        "content": bot_reply,
                        "timestamp": bot_msg.timestamp
                    },
                    "conversation_title": conv.title
                }
            
            # Handle format conversions with context preservation
            elif is_format_conversion:
                # Look for previous data to convert
                history = get_conversation_history(conv_id, db, limit=5)
                previous_data_found = False
                
                for prev_msg in reversed(history[:-1]):  # Exclude current message
                    if prev_msg["sender"] == "bot":
                        prev_content = prev_msg["content"]
                        
                        # Check if previous message had table/chart data
                        if isinstance(prev_content, list):
                            for block in prev_content:
                                if isinstance(block, dict) and block.get("type") in ["table", "chart"] and ("value_code" in block or "code" in block):
                                    # Found previous data - construct conversion request with context
                                    chart_type = "line chart" if "line" in user_input_lower else "bar chart" if "bar" in user_input_lower else "chart"
                                    
                                    # Extract the business context from the previous text block
                                    text_block = next((b for b in prev_content if b.get("type") == "text"), {})
                                    context_text = text_block.get("template", "")
                                    
                                    # Find year/period in the context
                                    prev_year = re.search(r"\b(20\d{2})\b", context_text)
                                    prev_period = re.search(r"q[1-4]|quarter|all years|all time", context_text.lower())
                                    
                                    time_context = ""
                                    if prev_year:
                                        time_context = f" in {prev_year.group(0)}"
                                    elif prev_period:
                                        time_context = f" for {prev_period.group(0)}"
                                    
                                    # Construct a complete request that includes the business context
                                    user_input = f"Show the same data as {chart_type}{time_context}"
                                    previous_data_found = True
                                    logger.info(f"[FORMAT CONVERSION] Converted to: {user_input}")
                                    break
                            
                            if previous_data_found:
                                break
                
                # If no previous data found, proceed normally
                if not previous_data_found:
                    user_input = msg.content.strip()
            else:
                # Check if this is a simple analytics query that should get latest year automatically
                analytics_keywords = [
                    "top", "best", "highest", "lowest", "sales", "revenue", "profit", "return", 
                    "customer", "product", "brand", "division", "performance", "analysis", 
                    "trend", "growth", "compare", "show me", "list", "which", "what", "how much"
                ]
                
                seems_like_analytics = any(keyword in user_input_lower for keyword in analytics_keywords)
                
                if seems_like_analytics:
                    # Smart year selection based on query context
                    if any(word in user_input_lower for word in ["last year", "previous year"]):
                        # For "last year" queries, use 2024
                        auto_year = 2024
                    elif any(word in user_input_lower for word in ["dashboard", "comprehensive", "overview", "trends", "monthly"]):
                        # For dashboard/overview queries, use 2024 (complete year data)
                        auto_year = 2024
                    elif any(word in user_input_lower for word in ["promotional", "campaign", "promo", "effectiveness"]):
                        # For promotional analysis, ALWAYS use 2025 (current campaigns)
                        auto_year = 2025
                        logger.info(f"[PROMOTIONAL YEAR] Forcing 2025 for promotional campaign analysis")
                    else:
                        # For ALL OTHER queries including underperforming, current analysis, use 2025 (recent data)
                        auto_year = 2025
                    
                    user_input = f"{user_input} in {auto_year}"
                    logger.info(f"[AUTO YEAR] Added year {auto_year} to query: {user_input}")
                    
                    # Don't try to inherit context for simple queries - just proceed
                else:
                    # Not an analytics query, proceed normally
                    user_input = msg.content.strip()

        # Generate conversation title if this is the first user message
        message_count = db.query(Message).filter(
            Message.conversation_id == conv_id,
            Message.sender == "user"
        ).count()
        
        if message_count == 1:
            try:
                llm_title = generate_llm_title(user_input)
                conv.title = llm_title
                db.commit()
            except Exception as e:
                logger.error(f"LLM title generation failed: {e}")
                conv.title = generate_smart_title(user_input)
                db.commit()

        # Handle completion requests for incomplete responses
        if needs_completion:
            logger.info("[COMPLETION] Completing underperforming SKUs query")
            # Force complete the underperforming SKUs query
            user_input = "which SKUs are underperforming in value and in margin in 2025"
        
        # Get conversation history and generate AI response
        history = get_conversation_history(conv_id, db, limit=20)
        
        try:
            raw_response = get_openai_response_fast(user_input, history)
            # Extract the response array from the fast response structure
            if isinstance(raw_response, dict) and "response" in raw_response:
                response_data = raw_response["response"]
            else:
                response_data = raw_response
            bot_reply = convert_decimals(parse_reply(response_data))
            
            # Additional validation to prevent formatting errors
            if not isinstance(bot_reply, list) or not bot_reply:
                logger.error(f"[RESPONSE ERROR] Invalid bot_reply format: {type(bot_reply)}")
                bot_reply = [{
                    "type": "text",
                    "template": "I encountered a technical issue. Please try rephrasing your question or contact support.",
                    "value_code": ""
                }]
        
        except Exception as llm_error:
            logger.error(f"[LLM ERROR] {llm_error}")
            bot_reply = [{
                "type": "text", 
                "template": "I encountered a technical issue while processing your request. Please try again with a different phrasing.",
                "value_code": ""
            }]
        
        # Save bot response
        bot_content = json.dumps(bot_reply)
        bot_msg = Message(conversation_id=conv_id, sender="bot", content=bot_content)
        db.add(bot_msg)
        db.commit()
        db.refresh(bot_msg)

        # Track analytics
        try:
            response_time_ms = int((time.time() - start_time) * 1000)
            analytics_service.track_query(
                db=db,
                query_text=user_input,
                user_id=str(user.id),
                session_id=str(conv_id),
                response_time_ms=response_time_ms,
                success=True,
                response_content=json.dumps(bot_reply)
            )
        except Exception as analytics_error:
            logger.warning(f"Analytics tracking failed: {analytics_error}")

        # ONLY clear pending_question after successful LLM response and DB save
        if hasattr(conv, "pending_question") and conv.pending_question:
            conv.pending_question = None
            db.commit()
            logger.info("[PENDING QUESTION] Cleared after successful response")

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
                "content": bot_reply,
                "timestamp": bot_msg.timestamp
            },
            "conversation_title": conv.title
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        # DON'T clear pending_question on errors - keep it for retry
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process message")

@router.get("/conversations/{conv_id}/messages/stream")
async def send_message_stream(
    conv_id: int, 
    content: str = Query(..., description="Message content"), 
    token: str = Query(..., description="Auth token"),  # 🔧 Auth via query param
    db: Session = Depends(get_db)
):
    """Send a message and get AI response via Server-Sent Events streaming"""
    
    # 🔒 Manual token validation for streaming
    try:
        user = get_user_from_token(db, token)
        if not user:
            raise HTTPException(status_code=403, detail="Invalid authentication token")
    except Exception as e:
        logger.error(f"Auth error in streaming: {e}")
        raise HTTPException(status_code=403, detail="Authentication failed")
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        start_time = time.time()
        
        try:
            # 🔒 Validate conversation
            logger.info(f"🌊 STREAMING: Processing message for conv_id={conv_id}, user_id={user.id}")
            
            conv = db.query(Conversation).filter(
                Conversation.id == conv_id, 
                Conversation.user_id == user.id
            ).first()
            
            if not conv:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Conversation not found'})}\n\n"
                return
            
            # 📝 Save user message
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing your query...'})}\n\n"
            await asyncio.sleep(0.1)  # Small delay for UX
            
            user_msg = Message(conversation_id=conv_id, sender="user", content=content)
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)
            
            # 📤 Stream user message
            yield f"data: {json.dumps({'type': 'user_message', 'content': {'id': user_msg.id, 'sender': 'user', 'content': content, 'timestamp': user_msg.timestamp.isoformat()}})}\n\n"
            
            # 🎯 Generate LLM title if first message
            message_count = db.query(Message).filter(
                Message.conversation_id == conv_id,
                Message.sender == "user"
            ).count()
            
            if message_count == 1:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Generating conversation title...'})}\n\n"
                try:
                    llm_title = generate_llm_title(content)
                    conv.title = llm_title
                    db.commit()
                    yield f"data: {json.dumps({'type': 'title_update', 'title': llm_title})}\n\n"
                except Exception as e:
                    logger.error(f"LLM title generation failed: {e}")
                    conv.title = generate_smart_title(content)
                    db.commit()
            
            # 🧠 AI Analysis
            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing query with AI intelligence...'})}\n\n"
            await asyncio.sleep(0.2)
            
            history = get_conversation_history(conv_id, db, limit=20)  # 🆕 Increased to 20
            
            # 🤖 Generate AI response with streaming
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating insights...'})}\n\n"
            
            # 🌊 NEW: Enhanced streaming with structured data
            accumulated_content = ""
            final_content = ""
            
            async for chunk in get_openai_response_stream_enhanced(content, history):
                chunk_type = chunk.get("type")
                
                if chunk_type == "stream_start":
                    yield f"data: {json.dumps({'type': 'stream_start', 'status': chunk['status'], 'complexity': chunk.get('complexity', 1)})}\n\n"
                
                elif chunk_type == "text_token":
                    # Stream individual tokens as they arrive
                    yield f"data: {json.dumps({'type': 'text_token', 'token': chunk['token'], 'accumulated': chunk['accumulated']})}\n\n"
                    accumulated_content = chunk["accumulated"]
                    await asyncio.sleep(0.02)  # Smooth streaming
                
                elif chunk_type == "parsing_start":
                    yield f"data: {json.dumps({'type': 'parsing_start', 'status': chunk['status']})}\n\n"
                
                elif chunk_type == "text_complete":
                    yield f"data: {json.dumps({'type': 'text_complete', 'content': chunk['content'], 'index': chunk['index']})}\n\n"
                
                elif chunk_type == "sql_start":
                    yield f"data: {json.dumps({'type': 'sql_start', 'title': chunk['title'], 'data_type': chunk['data_type'], 'index': chunk['index']})}\n\n"
                
                elif chunk_type == "table_data":
                    yield f"data: {json.dumps({'type': 'table_data', 'data': chunk['data'], 'index': chunk['index']})}\n\n"
                
                elif chunk_type == "chart_data":
                    yield f"data: {json.dumps({'type': 'chart_data', 'data': chunk['data'], 'index': chunk['index']})}\n\n"
                
                elif chunk_type == "sql_error":
                    yield f"data: {json.dumps({'type': 'sql_error', 'error': chunk['error'], 'index': chunk['index']})}\n\n"
                
                elif chunk_type == "stream_complete":
                    final_content = chunk["final_content"]
                    yield f"data: {json.dumps({'type': 'stream_complete', 'status': chunk['status']})}\n\n"
                    break
                
                elif chunk_type == "stream_error":
                    yield f"data: {json.dumps({'type': 'stream_error', 'error': chunk['error']})}\n\n"
                    return
            
            # 📝 Parse the final response into structured blocks
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing response into blocks...'})}\n\n"
            
            try:
                # 🔧 FIX: Use the same JSON parsing logic as regular endpoint
                parsed_json = parse_openai_response(final_content)
                
                # 🔧 Add validation like regular endpoint
                is_valid, error_msg = validate_response_structure(parsed_json)
                if not is_valid:
                    logger.error(f"Validation error: {error_msg}")
                    clean_reply = [{
                        "type": "text",
                        "template": "I generated an invalid response format. Please try again.",
                        "value_code": ""
                    }]
                else:
                    # 🔧 Enhance SQL queries like regular endpoint
                    for item in parsed_json:
                        if item.get("type") in ["table", "chart"]:
                            # Handle both "code" and "value_code" fields
                            sql_field = "value_code" if "value_code" in item else "code" if "code" in item else None
                            if sql_field:
                                original_sql = item[sql_field]
                                logger.info(f"[LLM GENERATED SQL] {original_sql}")
                                try:
                                    item[sql_field] = enhance_sql_query(original_sql)
                                    logger.info(f"[ENHANCED SQL] {item[sql_field]}")
                                except ValueError as e:
                                    logger.error(f"SQL validation error: {e}")
                                    clean_reply = [{
                                        "type": "text",
                                        "template": "I generated an unsafe SQL query. Please try again with a different approach.",
                                        "value_code": ""
                                    }]
                                    break
                    else:
                        # All SQL queries were valid, proceed with parsing
                        bot_reply = parse_reply(parsed_json)
                        clean_reply = convert_decimals(bot_reply)
                
            except Exception as parse_error:
                logger.error(f"Error parsing streaming response: {parse_error}")
                logger.error(f"Raw content: {final_content[:500]}...")
                
                # Fallback to simple text response
                clean_reply = [{
                    "type": "text",
                    "template": final_content if len(final_content) < 1000 else final_content[:1000] + "...",
                    "value_code": ""
                }]
            
            # 💾 Save bot response
            bot_content = json.dumps(clean_reply)
            bot_msg = Message(conversation_id=conv_id, sender="bot", content=bot_content)
            db.add(bot_msg)
            db.commit()
            db.refresh(bot_msg)
            
            # 📊 Stream response blocks progressively (charts/tables)
            if isinstance(clean_reply, list):
                for i, block in enumerate(clean_reply):
                    yield f"data: {json.dumps({'type': 'response_block', 'block': block, 'index': i, 'total': len(clean_reply)})}\n\n"
                    await asyncio.sleep(0.2)  # Progressive loading for UX
            else:
                yield f"data: {json.dumps({'type': 'response_block', 'block': clean_reply, 'index': 0, 'total': 1})}\n\n"
            
            # ✅ Complete
            response_time = int((time.time() - start_time) * 1000)
            yield f"data: {json.dumps({'type': 'complete', 'response_time_ms': response_time, 'bot_message_id': bot_msg.id})}\n\n"
            
            # 📈 Analytics (non-blocking)
            try:
                analytics_service.track_query(
                    db=db,
                    query_text=content,
                    user_id=str(user.id),
                    session_id=str(conv_id),
                    response_time_ms=response_time,
                    success=True,
                    response_content=json.dumps(clean_reply)
                )
            except Exception as analytics_error:
                logger.warning(f"Analytics tracking failed: {analytics_error}")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {str(e)}'})}\n\n"
        
        finally:
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

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