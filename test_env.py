# test_env.py

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="D:/03. EntrevistaTaking/.env")

print("OPENROUTER_API_KEY:", bool(os.getenv("OPENROUTER_API_KEY")))
print("OPENAI_API_KEY:", bool(os.getenv("OPENAI_API_KEY")))