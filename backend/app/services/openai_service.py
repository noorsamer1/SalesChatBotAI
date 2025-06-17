import json
from openai import OpenAI
from app.core.config import settings
from app.services.prompt_builder import build_final_prompt

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_openai_response(user_input: str) -> dict:
    # ✅ Step 1: Build dynamic system prompt
    system_prompt = build_final_prompt(user_input)

    # ✅ Step 2: Send to o4-mini
    # Consider GPT-4o-mini
    response = client.chat.completions.create(
        model="o4-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    # ✅ Step 3: Parse and return JSON result
    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON from OpenAI", "raw": content}
