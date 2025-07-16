from app.services.handlers.text_handler import handle_text
from app.services.handlers.table_handler import handle_table
from app.services.handlers.chart_handler import handle_chart
import json

# Dispatch Dictionary
handlers = {
    "text": handle_text,
    "chart": handle_chart,
    "table": handle_table,
    # Add more types as needed
}

def parse_reply(response):
    """
    Parses the LLM JSON response (single or multi-part) and routes each block to the correct handler.

    Args:
        response (str): The raw JSON string returned by the LLM.

    Returns:
        list: A list of processed backend-ready output blocks (text, table, chart, etc.).
    """
    multi_parse = response
    results = []

    # === Fallback: If response is None, empty, or not a dict/list, return error block ===
    if not multi_parse or not isinstance(multi_parse, (dict, list)):
        return [{
            "type": "text",
            "text": "Sorry, I could not answer your question. Please check your request or try rephrasing.",
            "value_code": ""
        }]

    # Multi-block (list) response
    if isinstance(multi_parse, list):
        for block in multi_parse:
            response_type = block.get("type")
            handler = handlers.get(response_type)
            if handler:
                results.append(handler(block))
            else:
                # Fallback for unsupported type
                results.append({
                    "type": "text",
                    "template": "Sorry, your request could not be processed (unsupported response type).",
                    "text": "Sorry, your request could not be processed (unsupported response type).",
                    "value_code": ""
                })
    else:
        # Single-block (dict) response
        response_type = multi_parse.get("type")
        handler = handlers.get(response_type)
        if handler:
            results.append(handler(multi_parse))
        else:
            # Fallback for unsupported type
            results.append({
                "type": "text",
                "template": "Sorry, your request could not be processed (unsupported response type).",
                "text": "Sorry, your request could not be processed (unsupported response type).",
                "value_code": ""
            })

    # Extra fallback if results is still empty
    if not results:
        results.append({
            "type": "text",
            "text": "Sorry, I could not answer your question. Please check your request or try rephrasing.",
            "value_code": ""
        })
    return results

