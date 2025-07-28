import json
import asyncio
import time
import re
from openai import OpenAI
from app.core.config import settings
from app.services.prompt_builder import build_modular_prompt, get_query_complexity_score
from app.services.mcp_tools import mcp_registry  # 🔧 Import MCP tools
from functools import wraps

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

def validate_and_fix_sql(sql_query: str) -> str:
    """Validate and fix common SQL GROUP BY/ORDER BY issues without duplicates"""
    if not sql_query.strip():
        return sql_query
    
    print(f"[SQL VALIDATOR] Input: {sql_query}")
    
    # 🚨 EMERGENCY FIX: DON'T TOUCH SUBQUERIES - Only fix main query
    if ('SELECT item_name_e' in sql_query and 
        'WHERE warehouse_name = (SELECT warehouse_name' in sql_query and
        'GROUP BY warehouse_name ORDER BY product_sales' in sql_query):
        # Only replace the LAST occurrence (main query), not the subquery
        parts = sql_query.rsplit('GROUP BY warehouse_name ORDER BY product_sales', 1)
        if len(parts) == 2:
            sql_query = parts[0] + 'GROUP BY item_name_e ORDER BY product_sales' + parts[1]
            print("[SQL VALIDATOR] 🚨 EMERGENCY FIX: Fixed branch product query (main query only)")
        else:
            sql_query = sql_query.replace(
                'GROUP BY warehouse_name ORDER BY product_sales',
                'GROUP BY item_name_e ORDER BY product_sales'
            )
            print("[SQL VALIDATOR] 🚨 EMERGENCY FIX: Fixed branch product query")
    
    # 🚨 CRITICAL FIX: Replace CURRENT_DATE with database-appropriate dates
    if 'CURRENT_DATE' in sql_query:
        print("[SQL VALIDATOR] Fixing CURRENT_DATE usage")
        # Replace last 3 months pattern
        if "CURRENT_DATE - INTERVAL '3 months'" in sql_query:
            sql_query = sql_query.replace(
                "job_date >= CURRENT_DATE - INTERVAL '3 months'",
                "yy = 2025 AND mm BETWEEN 3 AND 5"
            )
        # Replace last 12 months pattern  
        elif "CURRENT_DATE - INTERVAL '12 months'" in sql_query:
            sql_query = sql_query.replace(
                "job_date >= CURRENT_DATE - INTERVAL '12 months'",
                "(yy = 2024 OR yy = 2025)"
            )
        # Replace other CURRENT_DATE patterns
        else:
            sql_query = sql_query.replace("CURRENT_DATE", "'2025-05-18'")
        
        print(f"[SQL VALIDATOR] Fixed CURRENT_DATE: {sql_query}")
    
    # Check if GROUP BY columns are already correct
    if ('GROUP BY TO_CHAR(job_date' in sql_query and 
        'EXTRACT(YEAR FROM job_date)' in sql_query and 
        'EXTRACT(MONTH FROM job_date)' in sql_query):
        print("[SQL VALIDATOR] GROUP BY already contains required columns")
        return sql_query
    
    # Fix common GROUP BY issues with monthly trends
    if 'GROUP BY TO_CHAR(job_date' in sql_query and 'ORDER BY EXTRACT(' in sql_query:
        print("[SQL VALIDATOR] Fixing GROUP BY/ORDER BY compatibility")
        
        # Fix 1: Add missing GROUP BY columns for time-based grouping (only if not present)
        if ("GROUP BY TO_CHAR(job_date, 'Mon-YYYY')" in sql_query and 
            "EXTRACT(YEAR FROM job_date)" not in sql_query):
            sql_query = sql_query.replace(
                "GROUP BY TO_CHAR(job_date, 'Mon-YYYY')",
                "GROUP BY TO_CHAR(job_date, 'Mon-YYYY'), EXTRACT(YEAR FROM job_date), EXTRACT(MONTH FROM job_date)"
            )
        
        # Fix 2: Ensure ORDER BY uses the same expressions as GROUP BY
        if 'ORDER BY EXTRACT(MONTH FROM job_date)' in sql_query:
            sql_query = sql_query.replace(
                'ORDER BY EXTRACT(MONTH FROM job_date)',
                'ORDER BY EXTRACT(YEAR FROM job_date), EXTRACT(MONTH FROM job_date)'
            )
    
    # Fix specific GROUP BY issues
    import re
    
    # Fix GROUP BY mismatch - AGGRESSIVE approach
    if 'SELECT item_name_e' in sql_query and 'GROUP BY warehouse_name ORDER BY product_sales' in sql_query:
        sql_query = sql_query.replace(
            'GROUP BY warehouse_name ORDER BY product_sales',
            'GROUP BY item_name_e ORDER BY product_sales'
        )
        print("[SQL VALIDATOR] ✅ FIXED main query GROUP BY for item selection")
    
    # Additional safety check - catch any remaining GROUP BY mismatches (DISABLED - was corrupting subqueries)
    # if 'SELECT item_name_e' in sql_query and 'GROUP BY warehouse_name' in sql_query and 'ORDER BY product_sales' in sql_query:
    #     # More aggressive replacement
    #     import re
    #     sql_query = re.sub(
    #         r'GROUP BY warehouse_name(\s+ORDER BY product_sales)',
    #         r'GROUP BY item_name_e\1',
    #         sql_query
    #     )
    #     print("[SQL VALIDATOR] ✅ BACKUP FIX applied for GROUP BY")
    
    # Fix simple GROUP BY mismatch
    elif 'SELECT item_name_e' in sql_query and 'GROUP BY warehouse_name' in sql_query and sql_query.count('GROUP BY') == 1:
        sql_query = sql_query.replace('GROUP BY warehouse_name', 'GROUP BY item_name_e')
        print("[SQL VALIDATOR] Fixed GROUP BY to match SELECT columns")
    
    # Remove any duplicate GROUP BY columns (DISABLED - was corrupting queries)
    # group_by_match = re.search(r'GROUP BY\s+(.+?)(?=\s+ORDER BY|\s+HAVING|\s+LIMIT|$)', sql_query, re.IGNORECASE)
    # if group_by_match:
    #     group_by_clause = group_by_match.group(1)
    #     
    #     # Split columns and remove duplicates while preserving order
    #     columns = [col.strip() for col in group_by_clause.split(',')]
    #     unique_columns = []
    #     seen = set()
    #     
    #     for col in columns:
    #         if col.lower() not in seen:
    #             unique_columns.append(col)
    #             seen.add(col.lower())
    #     
    #     # Reconstruct the query with deduplicated GROUP BY
    #     new_group_by = 'GROUP BY ' + ', '.join(unique_columns)
    #     sql_query = re.sub(
    #         r'GROUP BY\s+.+?(?=\s+ORDER BY|\s+HAVING|\s+LIMIT|$)',
    #         new_group_by,
    #         sql_query,
    #         flags=re.IGNORECASE
    #     )
    
    # FINAL CHECK - Force fix GROUP BY issues at the very end (DISABLED - was corrupting subqueries)
    # if 'SELECT item_name_e' in sql_query and 'GROUP BY warehouse_name' in sql_query and 'product_sales' in sql_query:
    #     sql_query = sql_query.replace('GROUP BY warehouse_name', 'GROUP BY item_name_e')
    #     print("[SQL VALIDATOR] 🔥 FINAL EMERGENCY FIX - Forced GROUP BY correction")
    
    print(f"[SQL VALIDATOR] Output: {sql_query}")
    return sql_query

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
        "table": ["title"],  # Will check for value_code OR code separately
        "chart": ["title", "x", "y", "kind"]  # Will check for value_code OR code separately
    }
    
    for i, item in enumerate(response_data):
        if not isinstance(item, dict):
            return False, f"Item {i} must be an object"
        
        if "type" not in item:
            return False, f"Item {i} missing 'type' field"
        
        item_type = item["type"]
        if item_type not in required_fields:
            return False, f"Item {i} has unsupported type: {item_type}"
        
        # Check required fields
        missing_fields = [field for field in required_fields[item_type] if field not in item]
        if missing_fields:
            return False, f"Item {i} missing required fields: {missing_fields}"
        
        # Special validation for table/chart SQL field
        if item_type in ["table", "chart"]:
            if "value_code" not in item and "code" not in item:
                return False, f"Item {i} missing SQL field ('value_code' or 'code')"
    
    return True, "Valid"

def enhance_sql_query(sql_query: str) -> str:
    """Enhanced SQL queries with better formatting and safety"""
    if not sql_query.strip():
        return sql_query
    
    print(f"[SQL ENHANCER] Input: {sql_query}")
    
    # First validate and fix SQL syntax issues
    sql_query = validate_and_fix_sql(sql_query)
    
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
    
    print(f"[SQL ENHANCER] Output: {sql_query}")
    return sql_query

@retry_on_failure(max_retries=3, delay=1)
def get_openai_response_fast(user_input: str, conversation_history: list = None):
    """Fast OpenAI API call with optimized prompting and MCP tool integration"""
    
    # Type safety fix
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
    print(f"[FAST MODE] Processing query: {user_input[:100]}...")
    
    try:
        # 🔧 Analyze intent for MCP tools
        intent = analyze_query_intent(user_input)
        print(f"[FAST MODE] Intent analysis: {intent}")
        
        # 🔧 Execute MCP tools if needed (async wrapper for sync function)
        mcp_results = None
        if intent.get("mcp_tools"):
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                mcp_results = loop.run_until_complete(execute_mcp_tools_if_needed(user_input, intent))
            except RuntimeError:
                # Create new event loop if none exists
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                mcp_results = loop.run_until_complete(execute_mcp_tools_if_needed(user_input, intent))
            except Exception as e:
                print(f"[MCP] Error executing tools: {e}")
                mcp_results = None
        
        # Build enhanced system prompt with MCP context
        enhanced_system = build_modular_prompt(user_input, conversation_history)
        
        # Add MCP results to prompt if available
        if mcp_results:
            mcp_context = "\n\n🔧 ADVANCED ANALYTICS RESULTS:\n"
            for tool_name, result in mcp_results.items():
                mcp_context += f"\n**{tool_name.upper()}:**\n{json.dumps(result, indent=2)}\n"
            mcp_context += "\nIncorporate these advanced analytics insights into your response. Highlight key predictions and recommendations."
            enhanced_system += mcp_context
        
        # Dynamic parameters based on query complexity
        complexity_score = get_query_complexity_score(user_input)
        print(f"[FAST MODE] Complexity score: {complexity_score}")
        
        # Use gpt-4o-mini to avoid rate limits
        model = "gpt-4o-mini"
        
        print(f"[MODULAR PROMPT] Selected modules for: '{user_input}'")
        print(f"[MODULAR PROMPT] Prompt size: {len(enhanced_system)} chars")
        print(f"[FAST MODE] Using {model} with modular prompt ({len(enhanced_system)} chars)")
        
        if mcp_results:
            print(f"[FAST MODE] Enhanced with MCP results from: {list(mcp_results.keys())}")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_input}
            ],
            timeout=45,
            temperature=0.2,
            max_tokens=2500,
            top_p=0.95,
            frequency_penalty=0.1,
            presence_penalty=0.1
        )
        
        content = response.choices[0].message.content.strip()
        print(f"[LLM RAW OUTPUT] {content}")
        
        # Parse and validate response
        from app.services.improved_json_parser import parse_openai_response
        parsed_response = parse_openai_response(content)
        print(f"[FAST MODE] Parsed response: {parsed_response}")
        
        # 🔧 Enhanced SQL processing for both "code" and "value_code"
        for item in parsed_response:
            sql_field = None
            if item.get("type") in ["table", "chart"]:
                if "value_code" in item:
                    sql_field = "value_code"
                elif "code" in item:
                    # Convert "code" to "value_code" for consistency
                    item["value_code"] = item.pop("code")
                    sql_field = "value_code"
            
            if sql_field:
                original_sql = item[sql_field]
                print(f"[FAST MODE SQL] {original_sql}")
                
                # Handle LAG replacement if needed
                if "LAG(" in original_sql.upper():
                    simple_sql = original_sql.replace(
                        "ROUND(((SUM(sales_value) - LAG(SUM(sales_value)) OVER (ORDER BY brandname)) / NULLIF(LAG(SUM(sales_value)) OVER (ORDER BY brandname), 0)) * 100, 1) as growth_pct",
                        "ROUND(((SUM(CASE WHEN yy = 2024 THEN sales_value ELSE 0 END) - SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END)) / NULLIF(SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END), 0)) * 100, 1) as growth_pct"
                    )
                    if "WHERE yy = 2024" in simple_sql and "WHERE yy IN (2023, 2024)" not in simple_sql:
                        simple_sql = simple_sql.replace("WHERE yy = 2024", "WHERE yy IN (2023, 2024)")
                    item[sql_field] = simple_sql
                
                # Enhanced SQL with context
                enhanced_sql = enhance_sql_query(original_sql)
                item[sql_field] = enhanced_sql
                print(f"[FAST MODE ENHANCED SQL] {enhanced_sql}")
        
        # Validate response structure
        is_valid, error_msg = validate_response_structure(parsed_response)
        print(f"[FAST MODE] Validation result: {is_valid}, error: {error_msg}")
        
        if not is_valid:
            print(f"[FAST MODE] Validation failed: {error_msg}")
        
        return {"response": parsed_response}
        
    except Exception as e:
        print(f"[openai_service] Error in get_openai_response_fast: {e}")
        return {"response": [{"type": "text", "template": f"Error processing request: {str(e)}", "value_code": ""}]}

@retry_on_failure(max_retries=3, delay=1)
def get_openai_response(user_input: str, conversation_history: list = None) -> dict:
    """Enhanced OpenAI response with smart handling and validation"""
    try:
        # Handle different input types safely - CRITICAL FIX
        if isinstance(user_input, list):
            user_input = " ".join(str(item) for item in user_input)
        elif not isinstance(user_input, str):
            user_input = str(user_input)
        
        # Get query complexity to adjust parameters
        complexity = get_query_complexity_score(user_input)
        
        # Build enhanced prompt with context
        system_prompt = build_modular_prompt(user_input, conversation_history)
        
        # Add enhanced SQL guidelines to system prompt
        enhanced_sql_rules = """

CRITICAL SQL RULES FOR CHARTS AND TRENDS:

1. **Monthly Trend Queries - ALWAYS use this pattern:**
```sql
SELECT TO_CHAR(job_date, 'Mon-YYYY') as month,
       ROUND(SUM(sales_value), 3) as total_sales_kwd
FROM sales_data 
WHERE tran_type = 'Sales' AND EXTRACT(YEAR FROM job_date) = 2024
GROUP BY TO_CHAR(job_date, 'Mon-YYYY'), EXTRACT(YEAR FROM job_date), EXTRACT(MONTH FROM job_date)
ORDER BY EXTRACT(YEAR FROM job_date), EXTRACT(MONTH FROM job_date)
```

2. **When using GROUP BY with date functions:**
   - ALWAYS include both YEAR and MONTH in GROUP BY for monthly trends
   - ORDER BY must use the same expressions as GROUP BY
   - Never use raw job_date in ORDER BY when grouping by TO_CHAR

3. **Chart Query Patterns:**
   - X-axis: Use entity name or formatted date
   - Y-axis: Use aggregated values (SUM, AVG, COUNT)
   - Always GROUP BY the x-axis column
   - ORDER BY should match GROUP BY columns

WRONG: ❌
ORDER BY EXTRACT(MONTH FROM job_date) when GROUP BY TO_CHAR(job_date, 'Mon-YYYY')

RIGHT: ✅  
GROUP BY TO_CHAR(job_date, 'Mon-YYYY'), EXTRACT(YEAR FROM job_date), EXTRACT(MONTH FROM job_date)
ORDER BY EXTRACT(YEAR FROM job_date), EXTRACT(MONTH FROM job_date)
"""
        
        # Adjust parameters based on complexity
        max_tokens = min(4000, 1000 + (complexity * 500))
        temperature = max(0.1, 0.3 - (complexity * 0.05))
        
        # Enhanced system message
        enhanced_system = system_prompt + enhanced_sql_rules + f"""

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
            model="gpt-4o",
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
        print(f"[LLM RAW OUTPUT] {content}")  # Log raw LLM output
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
            
            # Enhance SQL queries in the response and fix field names
            for item in parsed_response:
                # Check for both "code" and "value_code" to handle LLM inconsistency
                sql_field = None
                if item.get("type") in ["table", "chart"]:
                    if "value_code" in item:
                        sql_field = "value_code"
                    elif "code" in item:
                        # Convert "code" to "value_code" for consistency
                        item["value_code"] = item.pop("code")
                        sql_field = "value_code"
                
                if sql_field:
                    original_sql = item[sql_field]
                    print(f"[LLM GENERATED SQL] {original_sql}")
                    try:
                        item[sql_field] = enhance_sql_query(original_sql)
                        print(f"[ENHANCED SQL] {item[sql_field]}")
                    except ValueError as e:
                        print(f"[openai_service] SQL validation error: {e}")
                        return [{
                            "type": "text",
                            "template": "I generated an unsafe SQL query. Please try again with a different approach.",
                            "value_code": ""
                        }]
            
            return {"response": parsed_response}
            
        except Exception as e:
            print(f"[LLM JSON ERROR] {e}")
            # Try to auto-fix using improved parser
            from .improved_json_parser import parse_openai_response as improved_parser
            try:
                parsed_response = improved_parser(content)
                is_valid, error_msg = validate_response_structure(parsed_response)
                if not is_valid:
                    print(f"[openai_service] Validation error after auto-fix: {error_msg}")
                    return [{
                        "type": "text",
                        "template": "Sorry, I had trouble formatting my answer. Please try rephrasing your question.",
                        "value_code": ""
                    }]
                return {"response": parsed_response}
            except Exception as e2:
                print(f"[LLM JSON AUTO-FIX FAILED] {e2}")
                return [{
                    "type": "text",
                    "template": "Sorry, I had trouble formatting my answer. Please try rephrasing your question.",
                    "value_code": ""
                }]
            
    except Exception as e:
        print(f"[openai_service] OpenAI API error: {e}")
        return [{
            "type": "text",
            "template": "I'm experiencing technical difficulties. Please try again or contact support if the problem persists.",
            "value_code": ""
        }]

async def get_openai_response_stream(user_input: str, conversation_history: list = None):
    """🌊 NEW: Streaming version that yields text chunks as they arrive from OpenAI"""
    
    # Type safety fix
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
    try:
        # Build the enhanced system prompt
        enhanced_system = build_modular_prompt(user_input, conversation_history)
        
        # Dynamic parameters based on query complexity
        complexity = get_query_complexity_score(user_input)
        temperature = min(0.2 + (complexity * 0.1), 0.7)
        max_tokens = min(2000 + (complexity * 500), 4000)
        
        enhanced_system += f"""

5. Format all monetary values in KWD with 3 decimal places
6. Use current date context: {time.strftime('%Y-%m-%d')}

Query Complexity Level: {complexity}/5
Response should be: {'detailed with multiple blocks' if complexity > 3 else 'focused and concise'}
"""
        
        # 🌊 Make STREAMING API call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_input}
            ],
            timeout=45,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            stream=True  # 🌊 Enable streaming
        )
        
        # 🌊 Yield chunks as they arrive
        accumulated_content = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                chunk_text = chunk.choices[0].delta.content
                accumulated_content += chunk_text
                yield {
                    "type": "text_chunk",
                    "content": chunk_text,
                    "accumulated": accumulated_content
                }
        
        # 🌊 Signal completion and return final parsed response
        yield {
            "type": "stream_complete",
            "final_content": accumulated_content
        }
        
    except Exception as e:
        print(f"[openai_service] Error in streaming: {e}")
        yield {
            "type": "error",
            "content": f"Error generating response: {str(e)}"
        }

async def get_openai_response_stream_enhanced(user_input: str, conversation_history: list = None):
    """🌊 Enhanced streaming that provides token-by-token AND structured data streaming"""
    
    # Type safety fix
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
    try:
        # Build the enhanced system prompt using modular approach
        enhanced_system = build_modular_prompt(user_input, conversation_history)
        
        # Dynamic parameters based on query complexity
        complexity = get_query_complexity_score(user_input)
        temperature = min(0.2 + (complexity * 0.1), 0.7)
        max_tokens = min(2000 + (complexity * 500), 4000)
        
        print(f"[ENHANCED STREAMING] Starting for query: {user_input[:50]}...")
        print(f"[ENHANCED STREAMING] Model: gpt-4o-mini, Complexity: {complexity}")
        
        # 🌊 Make STREAMING API call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_input}
            ],
            timeout=45,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            stream=True  # 🌊 Enable streaming
        )
        
        # 🎬 Start streaming with status
        yield {
            "type": "stream_start",
            "status": "AI is thinking...",
            "complexity": complexity
        }
        
        # 🌊 Yield individual tokens as they arrive
        accumulated_content = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                token = chunk.choices[0].delta.content
                accumulated_content += token
                yield {
                    "type": "text_token",
                    "token": token,
                    "accumulated": accumulated_content
                }
        
        # 🎯 Parse accumulated content for structured data
        yield {
            "type": "parsing_start", 
            "status": "Processing data structures..."
        }
        
        try:
            # Parse and validate the complete response
            from app.services.improved_json_parser import parse_openai_response
            parsed_response = parse_openai_response(accumulated_content)
            
            # 🎯 Stream structured data progressively
            for i, item in enumerate(parsed_response):
                if item.get("type") == "text":
                    yield {
                        "type": "text_complete",
                        "content": item.get("template", ""),
                        "index": i
                    }
                    
                elif item.get("type") in ["table", "chart"]:
                    # 🔧 Handle SQL execution and streaming
                    sql_field = "value_code" if "value_code" in item else "code" if "code" in item else None
                    if sql_field and item[sql_field]:
                        yield {
                            "type": "sql_start",
                            "title": item.get("title", "Data Analysis"),
                            "data_type": item["type"],
                            "index": i
                        }
                        
                        # Execute SQL and stream results
                        try:
                            from app.services.handlers.table_handler import handle_table_response
                            from app.services.handlers.chart_handler import handle_chart_response
                            
                            if item["type"] == "table":
                                result = handle_table_response(item)
                                yield {
                                    "type": "table_data", 
                                    "data": result,
                                    "index": i
                                }
                            elif item["type"] == "chart":
                                result = handle_chart_response(item)
                                yield {
                                    "type": "chart_data",
                                    "data": result, 
                                    "index": i
                                }
                                
                        except Exception as sql_error:
                            yield {
                                "type": "sql_error",
                                "error": str(sql_error),
                                "index": i
                            }
                    else:
                        yield {
                            "type": "data_error",
                            "error": "Missing SQL query",
                            "index": i
                        }
        
        except Exception as parse_error:
            print(f"[ENHANCED STREAMING] Parse error: {parse_error}")
            yield {
                "type": "parse_error",
                "error": f"Error parsing response: {str(parse_error)}",
                "raw_content": accumulated_content
            }
        
        # 🏁 Signal completion
        yield {
            "type": "stream_complete",
            "final_content": accumulated_content,
            "status": "Analysis complete!"
        }
        
    except Exception as e:
        print(f"[ENHANCED STREAMING] Error: {e}")
        yield {
            "type": "stream_error",
            "error": f"Streaming error: {str(e)}"
        }

def analyze_query_intent(user_input: str) -> dict:
    """Analyze user query to provide better responses"""
    
    # Handle different input types safely
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    elif not isinstance(user_input, str):
        user_input = str(user_input)
    
    intent = {
        "type": "general",
        "entities": [],
        "time_period": None,
        "metrics": [],
        "requires_chart": False,
        "requires_table": False,
        "mcp_tools": []  # 🔧 Add MCP tool detection
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
    
    # 🔧 MCP Tool Detection
    mcp_keywords = {
        "sales_forecasting": ["forecast", "predict", "future", "projection", "estimate", "what will", "next month", "next quarter"],
        "trend_analysis": ["trend", "pattern", "direction", "growing", "declining", "seasonal", "cycle"],
        "customer_behavior": ["customer behavior", "segment", "churn", "retention", "lifetime value", "rfm"],
        "inventory_prediction": ["inventory", "stock", "reorder", "demand", "supply", "shortage"],
        "market_segmentation": ["market segment", "clustering", "target market", "demographics"]
    }
    
    user_lower = user_input.lower()
    for tool_name, keywords in mcp_keywords.items():
        if any(keyword in user_lower for keyword in keywords):
            intent["mcp_tools"].append(tool_name)
    
    return intent

async def execute_mcp_tools_if_needed(user_input: str, intent: dict) -> dict:
    """Execute MCP tools if the query requires advanced analytics"""
    
    if not intent.get("mcp_tools"):
        return None
    
    print(f"[MCP] Detected tools needed: {intent['mcp_tools']}")
    
    mcp_results = {}
    
    for tool_name in intent["mcp_tools"]:
        try:
            # Extract parameters from user input
            params = extract_mcp_parameters(user_input, tool_name)
            print(f"[MCP] Executing {tool_name} with params: {params}")
            
            # Execute the tool
            result = await mcp_registry.execute_tool(tool_name, params)
            mcp_results[tool_name] = result
            
            print(f"[MCP] {tool_name} completed successfully")
            
        except Exception as e:
            print(f"[MCP] Error executing {tool_name}: {e}")
            mcp_results[tool_name] = {
                "type": "mcp_error",
                "tool": tool_name,
                "error": str(e)
            }
    
    return mcp_results

def extract_mcp_parameters(user_input: str, tool_name: str) -> dict:
    """Extract parameters for MCP tools from user input"""
    
    user_lower = user_input.lower()
    params = {}
    
    if tool_name == "sales_forecasting":
        # Extract timeframe
        if "1 month" in user_lower or "next month" in user_lower:
            params["timeframe"] = "1_month"
        elif "3 month" in user_lower or "quarter" in user_lower:
            params["timeframe"] = "3_months"
        elif "6 month" in user_lower:
            params["timeframe"] = "6_months"
        elif "year" in user_lower or "12 month" in user_lower:
            params["timeframe"] = "1_year"
        else:
            params["timeframe"] = "3_months"  # default
        
        # Extract entity (brand, customer, etc.)
        if "mccain" in user_lower:
            params["entity"] = "McCain"
        elif "alpro" in user_lower:
            params["entity"] = "Alpro"
        elif "total" in user_lower or "overall" in user_lower:
            params["entity"] = "total"
        else:
            params["entity"] = "total"  # default
    
    elif tool_name == "trend_analysis":
        params["metric"] = "sales_value"
        params["period"] = "monthly"
    
    elif tool_name == "customer_behavior":
        params["analysis_type"] = "rfm"
        if "churn" in user_lower:
            params["analysis_type"] = "churn"
        elif "segment" in user_lower:
            params["analysis_type"] = "segmentation"
    
    elif tool_name == "inventory_prediction":
        params["product"] = "all"
        # Extract specific product if mentioned
        if "mccain" in user_lower:
            params["product"] = "McCain"
    
    elif tool_name == "market_segmentation":
        params["criteria"] = "geographic"
        if "demographic" in user_lower:
            params["criteria"] = "demographic"
    
    return params