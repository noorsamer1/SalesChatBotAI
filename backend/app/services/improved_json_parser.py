import json
import re
from typing import Union, List, Dict, Any
from decimal import Decimal
import regex as re

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

def smart_json_parser(content: str) -> Union[List[Dict], Dict]:
    """
    Smart JSON parser that handles common OpenAI response formatting issues
    """
    
    # Step 1: Clean the content
    content = content.strip()
    
    # Remove markdown code blocks
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    
    # Remove any explanatory text before JSON
    json_start = re.search(r'[\[{]', content)
    if json_start:
        content = content[json_start.start():]
    
    # Remove any text after the last ] or }
    json_end = None
    brace_count = 0
    bracket_count = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(content):
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\' and in_string:
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                
            # If we've closed all brackets/braces, we're done
            if brace_count == 0 and bracket_count == 0 and (char == '}' or char == ']'):
                json_end = i + 1
                break
    
    if json_end:
        content = content[:json_end]
    
    # Step 2: Try to parse as-is first
    try:
        parsed = json.loads(content)
        return validate_and_fix_structure(parsed)
    except json.JSONDecodeError:
        pass
    
    # Step 3: Fix common JSON issues
    # Remove trailing commas
    content = re.sub(r',\s*}', '}', content)
    content = re.sub(r',\s*]', ']', content)
    
    # Try parsing again
    try:
        parsed = json.loads(content)
        return validate_and_fix_structure(parsed)
    except json.JSONDecodeError:
        pass
    
    # Step 4: More aggressive fixes
    # Fix SQL quotes in JSON strings (but be careful not to break valid JSON)
    content = fix_sql_in_json(content)
    
    try:
        parsed = json.loads(content)
        return validate_and_fix_structure(parsed)
    except json.JSONDecodeError as e:
        # Step 5: Last resort - try to extract valid JSON parts
        return extract_valid_json_parts(content)

def fix_sql_in_json(content: str) -> str:
    """
    Fix SQL quotes inside JSON strings without breaking JSON structure
    """
    # This is a more careful approach to fixing SQL quotes
    # We'll use regex to find SQL code patterns inside JSON strings
    
    def fix_sql_quotes(match):
        sql_content = match.group(0)
        # Fix common SQL quote issues
        sql_content = re.sub(r'tran_type = "Sales"', "tran_type = 'Sales'", sql_content)
        sql_content = re.sub(r'tran_type = "Sales Return"', "tran_type = 'Sales Return'", sql_content)
        sql_content = re.sub(r'= "([^"]*)"(?=\s+(AND|OR|GROUP|ORDER|LIMIT|FROM|WHERE))', r"= '\1'", sql_content)
        return sql_content
    
    # Find code sections in JSON
    content = re.sub(r'"code":\s*"([^"]*SELECT[^"]*)"', fix_sql_quotes, content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'"value_code":\s*"([^"]*SELECT[^"]*)"', fix_sql_quotes, content, flags=re.IGNORECASE | re.DOTALL)
    
    return content

def validate_and_fix_structure(parsed: Any) -> Union[List[Dict], Dict]:
    """
    Validate and fix the structure of parsed JSON
    """
    # Ensure it's always a list
    if isinstance(parsed, dict):
        parsed = [parsed]
    
    if not isinstance(parsed, list):
        raise ValueError("Response must be a JSON array")
    
    # Validate each item
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} must be an object")
        
        if "type" not in item:
            raise ValueError(f"Item {i} missing 'type' field")
        
        # Fix common issues
        item_type = item["type"]
        
        if item_type == "text":
            # Ensure template exists
            if "template" not in item:
                item["template"] = item.get("text", "No content")
            
            # Ensure value_code exists
            if "value_code" not in item:
                item["value_code"] = ""
                
        elif item_type == "table":
            # Ensure required fields exist
            if "title" not in item:
                item["title"] = "Data Table"
            # Handle both "code" and "value_code" fields
            if "value_code" not in item and "code" not in item:
                raise ValueError(f"Table item {i} missing 'value_code' or 'code' field")
            elif "code" in item and "value_code" not in item:
                # Convert "code" to "value_code" for consistency
                print(f"[JSON PARSER] Converting 'code' to 'value_code' for table item {i}")
                item["value_code"] = item.pop("code")
                
        elif item_type == "chart":
            # Ensure required fields exist
            if "title" not in item:
                item["title"] = "Chart"
            # Handle both "code" and "value_code" fields  
            if "value_code" not in item and "code" not in item:
                raise ValueError(f"Chart item {i} missing 'value_code' or 'code' field")
            elif "code" in item and "value_code" not in item:
                # Convert "code" to "value_code" for consistency
                print(f"[JSON PARSER] Converting 'code' to 'value_code' for chart item {i}")
                item["value_code"] = item.pop("code")
            if "x" not in item:
                raise ValueError(f"Chart item {i} missing 'x' field")
            if "y" not in item:
                raise ValueError(f"Chart item {i} missing 'y' field")
            if "kind" not in item:
                item["kind"] = "bar"
    
    return parsed

def extract_valid_json_parts(content: str) -> List[Dict]:
    """
    Last resort: try to extract valid JSON parts from malformed content
    """
    # Look for individual JSON objects
    objects = []
    
    # Pattern to match JSON objects
    object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    
    matches = re.findall(object_pattern, content)
    
    for match in matches:
        try:
            obj = json.loads(match)
            if isinstance(obj, dict) and "type" in obj:
                objects.append(obj)
        except json.JSONDecodeError:
            continue
    
    if objects:
        return validate_and_fix_structure(objects)
    
    # Check if the content looks like a refusal response
    content_lower = content.lower()
    if any(phrase in content_lower for phrase in [
        "sorry, i can only answer", 
        "i specialize in sales analytics",
        "not about sales", 
        "sales-related question",
        "sales analytics",
        "business analytics"
    ]):
        return [{
            "type": "text",
            "template": "Sorry, I can only answer questions about sales and sales analytics. Please ask a sales-related question.",
            "value_code": ""
        }]
    
    # If nothing works, return a fallback
    return [{
        "type": "text",
        "template": "I encountered a formatting error. Please try rephrasing your question.",
        "value_code": ""
    }]

# Update the main OpenAI service to use the improved parser
def parse_openai_response(content: str) -> List[Dict]:
    """
    Enhanced parser for OpenAI responses with smart suggestions extraction
    """
    
    # First extract smart suggestions if they exist
    smart_suggestions = []
    suggestions_pattern = r'\*\*Smart Suggestions:\*\*\s*\n((?:- .+\n?)+)'
    suggestions_match = re.search(suggestions_pattern, content, re.MULTILINE)
    if suggestions_match:
        suggestions_text = suggestions_match.group(1)
        # Extract individual suggestions
        for line in suggestions_text.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                smart_suggestions.append(line[2:])  # Remove '- ' prefix
        
        # Remove smart suggestions from content for JSON parsing
        content = re.sub(suggestions_pattern, '', content)
    
    # Parse the main JSON response
    try:
        # Use existing smart JSON parser
        response_data = smart_json_parser(content)
        
        # Ensure it's a list
        if not isinstance(response_data, list):
            response_data = [response_data] if response_data else []
        
        # Add smart suggestions as a separate block if they exist
        if smart_suggestions:
            response_data.append({
                "type": "smart_suggestions",
                "suggestions": smart_suggestions
            })
        
        # Validate and fix structure
        response_data = validate_and_fix_structure(response_data)
        
        return response_data
        
    except Exception as e:
        print(f"[JSON PARSER] Error parsing response: {e}")
        print(f"[JSON PARSER] Content: {content[:500]}...")
        
        # Fallback for plain text responses
        return [{
            "type": "text",
            "template": content.strip(),
            "value_code": ""
        }]