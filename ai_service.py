import os
import google.generativeai as genai
from dotenv import load_dotenv

# Setup
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

model = None

if api_key:
    genai.configure(api_key=api_key)
    print("🔄 Connecting to AI...")
    
    try:
        # 1. Ask Google what models are available for this Key
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 2. Smart Selection Logic
        chosen_model = None
        
        # Preference List (Newest to Oldest)
        preferences = ['models/gemini-1.5-flash', 'models/gemini-pro', 'models/gemini-1.0-pro']
        
        # Try to find a preferred model
        for pref in preferences:
            if pref in available_models:
                chosen_model = pref
                break
        
        # Fallback: Just take the first one available
        if not chosen_model and available_models:
            chosen_model = available_models[0]
            
        if chosen_model:
            print(f"✅ AI Connected using: {chosen_model}")
            model = genai.GenerativeModel(chosen_model)
        else:
            print("❌ No text-generation models found for this API Key.")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

else:
    print("⚠️ Warning: GEMINI_API_KEY not found.")

SYSTEM_PROMPT = """
You are a helpful, professional Ethiopian consultant for the USA Diversity Visa (DV) Program. 
- Answer clearly and concisely.
- Answer in the same language as the user (Amharic or English).
- The service fee is 300 ETB.
- The DV Application itself is free, but they are paying for our expert filling service.
- Photo Rule: White background, no glasses, look straight.
"""

async def ask_gemini(user_text):
    if not model:
        return "⚠️ System Error: AI model is not connected. Please check server logs."
    
    try:
        prompt = f"{SYSTEM_PROMPT}\n\nUser Question: {user_text}"
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        return f"Sorry, I am having trouble connecting to the AI right now. Error: {str(e)}"