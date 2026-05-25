import os
from dotenv import load_dotenv
from supabase import create_client
from google import genai as google_genai
from openai import OpenAI

load_dotenv()

supabase      = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
gemini_client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
HF_TOKEN      = os.environ.get("HF_TOKEN", "")
W3W_KEY       = os.environ.get("W3W_API_KEY", "")
