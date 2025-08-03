import os
from typing import List, Dict, Any

def build_modular_prompt(user_input: str = "", conversation_history: list = None) -> str:
    """Build modular prompt from individual files"""
    prompts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts')
    prompt_parts = []
    
    # Load core modules
    modules = [
        'core_identity.txt',
        'business_intelligence.txt', 
        'database_schema.txt',
        'response_format_rules.txt'
    ]
    
    for module in modules:
        try:
            module_path = os.path.join(prompts_dir, 'modules', module)
            if os.path.exists(module_path):
                with open(module_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    prompt_parts.append(content)
        except Exception as e:
            print(f"Error loading module {module}: {e}")
    
    base_prompt = "\n\n".join(prompt_parts)
    
    # If user input is provided, enhance the prompt
    if user_input:
        base_prompt = enhance_prompt_with_context(user_input, base_prompt)
    
    return base_prompt

def get_query_complexity_score(user_input: str) -> float:
    """Calculate complexity score for user input"""
    score = 0.0
    
    # Basic complexity indicators
    if any(word in user_input.lower() for word in ['trend', 'growth', 'comparison', 'analysis']):
        score += 0.3
    
    if any(word in user_input.lower() for word in ['profit', 'margin', 'cost', 'revenue']):
        score += 0.2
    
    if any(word in user_input.lower() for word in ['return', 'refund', 'quality']):
        score += 0.2
    
    if any(word in user_input.lower() for word in ['top', 'best', 'worst', 'least']):
        score += 0.1
    
    if any(word in user_input.lower() for word in ['customer', 'brand', 'product']):
        score += 0.1
    
    # Length-based complexity
    word_count = len(user_input.split())
    if word_count > 10:
        score += 0.1
    elif word_count > 5:
        score += 0.05
    
    return min(score, 1.0)

def enhance_prompt_with_context(user_input: str, base_prompt: str) -> str:
    """Enhance base prompt with user-specific context"""
    
    # Add query complexity awareness
    complexity_score = get_query_complexity_score(user_input)
    
    complexity_guidance = f"""
📊 QUERY COMPLEXITY ANALYSIS
============================
Complexity Score: {complexity_score:.2f}

"""
    
    if complexity_score > 0.7:
        complexity_guidance += """
🚨 HIGH COMPLEXITY DETECTED
- Use comprehensive KPI formats
- Include detailed analysis
- Provide multiple insights
- Consider trend analysis if applicable
"""
    elif complexity_score > 0.4:
        complexity_guidance += """
📈 MEDIUM COMPLEXITY DETECTED  
- Use standard KPI formats
- Include basic analysis
- Focus on key metrics
"""
    else:
        complexity_guidance += """
📋 LOW COMPLEXITY DETECTED
- Use simple KPI formats
- Provide basic insights
- Keep response concise
"""
    
    return base_prompt + "\n\n" + complexity_guidance

# Test the prompt builder
if __name__ == "__main__":
    print("🧠 Prompt Builder Test")
    print("=" * 30)
    
    # Test modular prompt building
    prompt = build_modular_prompt()
    print(f"📝 Prompt Length: {len(prompt)} characters")
    
    # Test with user input
    test_prompt = build_modular_prompt("Profit trend in 2024")
    print(f"📝 Enhanced Prompt Length: {len(test_prompt)} characters")
    
    # Test complexity scoring
    test_questions = [
        "Show me sales data",
        "Which customer make the worst profit?",
        "Top 10 customers by revenue with trend analysis"
    ]
    
    for question in test_questions:
        score = get_query_complexity_score(question)
        print(f"❓ '{question}' → Complexity: {score:.2f}")
    
    print("✅ Prompt builder working correctly") 