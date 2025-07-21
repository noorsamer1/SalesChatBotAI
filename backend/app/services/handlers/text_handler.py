from .handlersCommnFunction import *
import re

def handle_text(response):
    """Enhanced text handler with better formatting and insights"""
    
    try:
        template = response.get("template") or response.get("text") or ""
        value_code = response.get("value_code", "").strip()
        

        if not template:
            result = {
                "type": "text",
                "template": "⚠️ No template provided for text response"
            }
            # --- Add normalization here ---
            if "text" not in result and "template" in result:
                result["text"] = result["template"]
            if "template" not in result and "text" in result:
                result["template"] = result["text"]
            return result

        # If there's no value_code, just return the template as-is
        if not value_code:
            result = {
                "type": "text",
                "template": template
            }
            if "text" not in result and "template" in result:
                result["text"] = result["template"]
            if "template" not in result and "text" in result:
                result["template"] = result["text"]
            return result

        values = {}

        try:
            rows, columns = execute_query_safely(value_code)

            if rows and len(rows) > 0:
                row = rows[0]
                # Map column names to values
                for i, col in enumerate(columns):
                    if i < len(row):
                        value = row[i]
                        # Format based on column name
                        if any(keyword in col.lower() for keyword in ['sales', 'revenue', 'profit', 'value']):
                            values[col] = format_currency(value)
                        elif any(keyword in col.lower() for keyword in ['growth', 'margin', 'percent']):
                            values[col] = f"{float(value or 0):.1f}%"
                        else:
                            values[col] = str(value) if value is not None else "0"
                # Support old format with single {value} placeholder
                if len(columns) == 1 and "{value}" in template:
                    values["value"] = values.get(columns[0], "0")
            else:
                # No data returned from text query - but this doesn't mean no data exists overall
                # Use a generic message or the original template without placeholders
                if template and "{" in template:
                    # Remove placeholder syntax and provide a generic message
                    cleaned_template = template
                    cleaned_template = re.sub(r'\{[^}]+\}', 'data', cleaned_template)
                    result = {
                        "type": "text", 
                        "template": cleaned_template,
                        "value_code": ""
                    }
                else:
                    # Fallback to original template
                    result = {
                        "type": "text",
                        "template": template or "Analysis completed.",
                        "value_code": ""
                    }
                if "text" not in result and "template" in result:
                    result["text"] = result["template"]
                if "template" not in result and "text" in result:
                    result["template"] = result["text"]
                return result

        except Exception as e:
            logger.error(f"Error executing text query: {e}")
            result = {
                "type": "text",
                "template": f"⚠️ Error retrieving data: {str(e)}"
            }
            if "text" not in result and "template" in result:
                result["text"] = result["template"]
            if "template" not in result and "text" in result:
                result["template"] = result["text"]
            return result

        # Format the template with values
        try:
            # If no placeholders found, just return the template
            if not re.search(r'\{[^}]+\}', template):
                result = {
                    "type": "text",
                    "template": template
                }
                if "text" not in result and "template" in result:
                    result["text"] = result["template"]
                if "template" not in result and "text" in result:
                    result["template"] = result["text"]
                return result
            final_text = template.format(**values)
            logger.info(f"[DEBUG TEXT HANDLER] template: {template}, value_code: {value_code}, values: {values}")
        except KeyError as e:
            logger.error(f"Template formatting error: {e}")
            final_text = template
        except ValueError as e:
            logger.error(f"Template value error: {e}")
            final_text = template

        result = {
            "type": "text",
            "template": final_text
        }
        if "text" not in result and "template" in result:
            result["text"] = result["template"]
        if "template" not in result and "text" in result:
            result["template"] = result["text"]
        return result

    except Exception as e:
        logger.error(f"Text handler error: {e}")
        result = {
            "type": "text",
            "template": f"⚠️ Error processing text response: {str(e)}"
        }
        if "text" not in result and "template" in result:
            result["text"] = result["template"]
        if "template" not in result and "text" in result:
            result["template"] = result["text"]
        return result