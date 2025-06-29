from app.services.handlers.text_handler import handle_text
from app.services.handlers.table_handler import handle_table
from app.services.handlers.chart_handler import handle_chart

# Dispatch Dictonary
handlers = {
    "text": handle_text,
    "chart": handle_chart,
    "table": handle_table,
    # Add more types as needed
}

def parse_reply(response):
    response_type = response.get("type")
    handler = handlers.get(response_type)

    if handler:
        return handler(response)
    else:
        raise ValueError(f"Unsupported response type: {response_type}")