import json
import asyncio
import time
from openai import OpenAI
from app.core.config import settings
from app.services.prompt_builder import build_final_prompt, get_query_complexity_score
from functools import wraps
import re

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def retry_on_failure(max_retries=3, delay=1):
    """Decorator for retrying OpenAI API calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    print(f"[openai_service] Retry {attempt + 1}/{max_retries} after error: {e}")
            return None
        return wrapper
    return decorator

def clean_json_response(content: str) -> str:
    """Clean and fix common JSON formatting issues"""
    # Remove markdown code blocks
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    
    # Remove any text before the first [ or {
    json_start = re.search(r'[\[{]', content)
    if json_start:
        content = content[json_start.start():]
    
    # Remove any text after the last ] or }
    json_end = None
    for i, char in enumerate(reversed(content)):
        if char in ']}':
            json_end = len(content) - i
            break
    
    if json_end:
        content = content[:json_end]
    
    # Fix trailing commas BEFORE fixing quotes
    content = re.sub(r',\s*}', '}', content)  # Remove trailing commas in objects
    content = re.sub(r',\s*]', ']', content)  # Remove trailing commas in arrays
    
    # DON'T automatically convert single quotes to double quotes
    # This was causing SQL syntax errors
    # Only fix quotes that are clearly JSON property names or string values
    # We'll let Python's json.loads handle the parsing
    
    return content.strip()

def fix_sql_quotes(sql_string: str) -> str:
    """Fix SQL string quotes that were corrupted during JSON cleaning"""
    # Common fixes for SQL syntax
    sql_string = sql_string.replace('tran_type = "Sales"', "tran_type = 'Sales'")
    sql_string = sql_string.replace('tran_type = "Sales Return"', "tran_type = 'Sales Return'")
    
    # Fix other common SQL string literals
    sql_string = re.sub(r'= "([^"]*)"', r"= '\1'", sql_string)
    sql_string = re.sub(r'IN \("([^"]*)"', r"IN ('\1'", sql_string)
    
    return sql_string

def validate_response_structure(response_data) -> tuple[bool, str]:
    """Validate the structure of LLM response"""
    if not isinstance(response_data, list):
        return False, "Response must be a JSON array"
    
    required_fields = {
        "text": ["template"],
        "table": ["title", "code"],
        "chart": ["title", "code", "x", "y", "kind"]
    }
    
    for i, item in enumerate(response_data):
        if not isinstance(item, dict):
            return False, f"Item {i} must be an object"
        
        if "type" not in item:
            return False, f"Item {i} missing 'type' field"
        
        item_type = item["type"]
        if item_type not in required_fields:
            return False, f"Item {i} has unsupported type: {item_type}"
        
        missing_fields = [field for field in required_fields[item_type] if field not in item]
        if missing_fields:
            return False, f"Item {i} missing required fields: {missing_fields}"
    
    return True, "Valid"

def enhance_sql_query(sql_query: str) -> str:
    """Enhance SQL queries with better formatting and safety"""
    if not sql_query.strip():
        return sql_query
    
    # Add safety checks
    dangerous_keywords = ['DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
    upper_query = sql_query.upper()
    
    for keyword in dangerous_keywords:
        if keyword in upper_query:
            raise ValueError(f"Query contains dangerous keyword: {keyword}")
    
    # Add query optimizations
    if 'ORDER BY' not in upper_query and 'LIMIT' in upper_query:
        # Add ordering for consistent results when using LIMIT
        if 'GROUP BY' in upper_query:
            sql_query = sql_query.replace('LIMIT', 'ORDER BY 1 DESC LIMIT')
        else:
            sql_query = sql_query.replace('LIMIT', 'ORDER BY job_date DESC LIMIT')
    
    return sql_query

@retry_on_failure(max_retries=3, delay=1)
def get_openai_response(user_input: str, conversation_history: list = None) -> dict:
    """Enhanced OpenAI response with smart handling and validation"""
    try:
        # Get query complexity to adjust parameters
        complexity = get_query_complexity_score(user_input)
        
        # Build enhanced prompt with context
        system_prompt = build_final_prompt(user_input, conversation_history)
        
        # Adjust parameters based on complexity
        max_tokens = min(4000, 1000 + (complexity * 500))
        temperature = max(0.1, 0.3 - (complexity * 0.05))
        
        # Enhanced system message
        enhanced_system = system_prompt + f"""

IMPORTANT RESPONSE GUIDELINES:
1. Always return a valid JSON array, even for single responses: [{{"type": "text", "template": "...", "value_code": "..."}}]
2. For complex queries, provide multi-block responses with text summary + table/chart
3. Include business insights and recommendations in text responses
4. Validate all SQL queries for safety and accuracy
5. Format all monetary values in KWD with 3 decimal places
6. Use current date context: {time.strftime('%Y-%m-%d')}

Query Complexity Level: {complexity}/5
Response should be: {'detailed with multiple blocks' if complexity > 3 else 'focused and concise'}
"""
        
        # Make API call with enhanced parameters
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_input}
            ],
            timeout=45,  # Increased timeout for complex queries
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            frequency_penalty=0.1,
            presence_penalty=0.1
        )
        
        content = response.choices[0].message.content
        
        if not content:
            return [{
                "type": "text",
                "template": "I couldn't generate a response. Please try rephrasing your question.",
                "value_code": ""
            }]
        
        # Clean and parse JSON using improved parser
        try:
            from app.services.improved_json_parser import parse_openai_response
            parsed_response = parse_openai_response(content)
            
            # Validate structure
            is_valid, error_msg = validate_response_structure(parsed_response)
            if not is_valid:
                print(f"[openai_service] Validation error: {error_msg}")
                return [{
                    "type": "text",
                    "template": "I generated an invalid response format. Please try again.",
                    "value_code": ""
                }]
            
            # Enhance SQL queries in the response
            for item in parsed_response:
                if item.get("type") in ["table", "chart"] and "code" in item:
                    print("[LLM GENERATED SQL]", item["code"])
                    try:
                        item["code"] = enhance_sql_query(item["code"])
                    except ValueError as e:
                        print(f"[openai_service] SQL validation error: {e}")
                        return [{
                            "type": "text",
                            "template": "I generated an unsafe SQL query. Please try again with a different approach.",
                            "value_code": ""
                        }]
            
            return parsed_response
            
        except json.JSONDecodeError as e:
            print(f"[openai_service] JSON decode error: {e}")
            print(f"[openai_service] Raw content: {content}")
            # print(f"[openai_service] Cleaned content: {cleaned_content}")
            
            # Try to extract meaningful text if JSON parsing fails
            return [{
                "type": "text",
                "template": "I had trouble formatting my response. Here's what I found: " + content[:500],
                "value_code": ""
            }]
            
    except Exception as e:
        print(f"[openai_service] OpenAI API error: {e}")
        return [{
            "type": "text",
            "template": "I'm experiencing technical difficulties. Please try again or contact support if the problem persists.",
            "value_code": ""
        }]

def analyze_query_intent(user_input: str) -> dict:
    """Analyze user query to provide better responses"""
    intent = {
        "type": "general",
        "entities": [],
        "time_period": None,
        "metrics": [],
        "requires_chart": False,
        "requires_table": False
    }
    
    # Detect entity types
    entities = {
        "customer": ["customer", "client", "buyer"],
        "product": ["product", "item", "brand"],
        "salesperson": ["sales", "salesman", "rep"],
        "division": ["division", "department"],
        "time": ["month", "year", "quarter", "ytd", "mtd"]
    }
    
    for entity_type, keywords in entities.items():
        if any(keyword in user_input.lower() for keyword in keywords):
            intent["entities"].append(entity_type)
    
    # Detect metrics
    metrics = ["revenue", "sales", "profit", "margin", "return", "growth", "performance"]
    intent["metrics"] = [metric for metric in metrics if metric in user_input.lower()]
    
    # Detect visualization needs
    chart_keywords = ["chart", "graph", "trend", "visual", "plot"]
    table_keywords = ["table", "list", "top", "ranking", "breakdown"]
    
    intent["requires_chart"] = any(keyword in user_input.lower() for keyword in chart_keywords)
    intent["requires_table"] = any(keyword in user_input.lower() for keyword in table_keywords)
    
    return intent