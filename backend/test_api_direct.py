#!/usr/bin/env python3
"""
Direct test of OpenAI API to debug the refusal issue
"""
import sys
sys.path.append('.')

from openai import OpenAI
from app.core.config import settings
from app.services.prompt_builder import build_modular_prompt

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def test_direct_api():
    """Test direct API call to see what the LLM is actually responding"""
    
    queries = [
        "Show me items that were sold outside their normal shelf life range",
        "Which sales representative generated the most profit last month?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"🧪 TEST {i}: {query}\n")
        
        try:
            # Build the modular prompt
            system_prompt = build_modular_prompt(query)
            
            print(f"📊 System Prompt Length: {len(system_prompt)} chars")
            
            print("\n🤖 MAKING API CALL...")
            
            # Make the API call
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            print(f"\n📤 LLM RESPONSE ({len(content)} chars):")
            print("-" * 60)
            print(content[:500] + ("..." if len(content) > 500 else ""))
            print("-" * 60)
            
            # Analyze the response
            if "sorry" in content.lower() and "only answer questions about sales" in content.lower():
                print("❌ STILL REFUSING!")
            else:
                print("✅ PROPER RESPONSE PROVIDED")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    test_direct_api() 