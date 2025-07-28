from app.services.handlers.table_handler import handle_table
from app.services.handlers.chart_handler import handle_chart
from app.services.handlers.text_handler import handle_text

def parse_reply(reply_data):
    """
    Parse the reply data and convert it into the format expected by the frontend.
    """
    if not isinstance(reply_data, list):
        return {"error": "Invalid reply format"}
    
    result = []
    
    for i, block in enumerate(reply_data):
        response_type = block.get("type", "unknown")
        print(f"[RESPONSE PARSER] Block {i}: type='{response_type}', block={block}")
        
        try:
            if response_type == "text":
                handler = handle_text
            elif response_type == "table":
                handler = handle_table
            elif response_type == "chart":
                handler = handle_chart
            elif response_type == "smart_suggestions":
                # Handle smart suggestions directly
                print(f"[RESPONSE PARSER] Processing smart suggestions: {block.get('suggestions', [])}")
                result.append({
                    "type": "smart_suggestions",
                    "suggestions": block.get("suggestions", [])
                })
                continue
            else:
                print(f"[RESPONSE PARSER] No handler found for type '{response_type}'")
                result.append({
                    "type": "error",
                    "content": f"Unsupported response type: {response_type}"
                })
                continue
            
            print(f"[RESPONSE PARSER] Found handler for type '{response_type}'")
            processed_block = handler(block)
            result.append(processed_block)
            
        except Exception as e:
            print(f"[RESPONSE PARSER] Error processing block {i}: {e}")
            result.append({
                "type": "error",
                "content": f"Error processing {response_type} block: {str(e)}"
            })
    
    return result

