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
    # Parse the JSON string from the LLM
    multi_parse = response

    # Initialize a list to collect results
    results = []

    # If the response is a list (multi-response)
    if isinstance(multi_parse, list):
        for block in multi_parse:
            response_type = block.get("type")
            handler = handlers.get(response_type)
            if handler:
                results.append(handler(block))
            else:
                raise ValueError(f"Unsupported response type: {response_type}")
    else:
        # Single response block (dict)
        response_type = multi_parse.get("type")
        handler = handlers.get(response_type)
        if handler:
            results.append(handler(multi_parse))
        else:
            raise ValueError(f"Unsupported response type: {response_type}")

    return results
