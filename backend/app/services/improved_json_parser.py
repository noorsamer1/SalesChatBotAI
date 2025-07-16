import json
import re
from typing import Union, List, Dict, Any
import regex as re
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
            if "code" not in item:
                raise ValueError(f"Table item {i} missing 'code' field")
                
        elif item_type == "chart":
            # Ensure required fields exist
            if "title" not in item:
                item["title"] = "Chart"
            if "code" not in item:
                raise ValueError(f"Chart item {i} missing 'code' field")
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
    
    # If nothing works, return a fallback
    return [{
        "type": "text",
        "template": "I encountered a formatting error. Please try rephrasing your question.",
        "value_code": ""
    }]

# Update the main OpenAI service to use the improved parser
def parse_openai_response(content: str) -> List[Dict]:
    """
    Main function to parse OpenAI responses with robust error handling
    """
    if not content or not content.strip():
        return [{
            "type": "text",
            "template": "No response received. Please try again.",
            "value_code": ""
        }]
    
    try:
        parsed = smart_json_parser(content)
        return parsed
    except Exception as e:
        print(f"[json_parser] Error parsing response: {e}")
        print(f"[json_parser] Raw content: {content}")
        
        return [{
            "type": "text",
            "template": f"Response parsing error. Please try a different question.",
            "value_code": ""
        }]