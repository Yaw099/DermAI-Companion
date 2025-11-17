import os
from openai import OpenAI

def ask_ai(conversation):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "(Demo) AI is not configured properly. Add your OpenAI API key"
    
    try:
        client = OpenAI(api_key=api_key)
    
        messages = [{"role": "system", "content": "You are a helpful dermatology educational assistant. You provide specific information about questions users have about their skin conditions, but never give any real medical advice, prompting users to consult their dermatologist for an official diagnosis."}]
        for msg in conversation:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Error: {str(e)}"