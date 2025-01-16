import google.generativeai as genai
import os

GOOGLE_API_KEY = "AIzaSyD-XWqBkxRugFITFOTfliIge3thpmz9bL0"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def get_response_from_model(user_input):
    try:
        response = model.generate_content(user_input)
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return "Sorry, something went wrong. Please try again later."
    
    
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
