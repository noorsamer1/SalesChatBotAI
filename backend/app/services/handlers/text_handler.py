from app.core.db import engine
from sqlalchemy import text

def handle_text(response):
    code = response.get("value_code", "").strip()
    value = ""

    if code:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(code))
                row = result.fetchone()
                value = row[0] if row else ""
        except Exception as e:
            value = f"[DB ERROR: {e}]"

    final_text = response["template"].format(value=value)

    return {
        "type": "text",
        "text": final_text
    }
