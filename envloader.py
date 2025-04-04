# envloader.py
import os
from dotenv import load_dotenv
import openai

load_dotenv("openaiapi.env")
openai.api_key = os.getenv("OPENAI_API_KEY")