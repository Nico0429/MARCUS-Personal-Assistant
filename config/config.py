import os
from dotenv import load_dotenv

# Load the vault
load_dotenv()

# --- SECRETS (Pulled from .env) ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

# --- AI SETTINGS ---
MODEL_NAME = "llama3.2:1b" 

# --- AI PARAMETERS ---
# 0.1 is very literal (good for lists), 0.7 is more creative
TEMPERATURE = 0.2

