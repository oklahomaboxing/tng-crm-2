import os

from openai import OpenAI


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
