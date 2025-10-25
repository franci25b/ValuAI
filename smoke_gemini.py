import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("Set GEMINI_API_KEY in your environment (e.g., in .env).")

client = genai.Client(api_key=api_key)
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Say 'pong' if you can read this."
)
print(resp.text)
