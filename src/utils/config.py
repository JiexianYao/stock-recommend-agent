"""配置管理，从 .env 加载。"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    # Provider: "gemini" | "openai"
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

    # Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Search
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

    # Agent
    MAX_TOOL_ROUNDS = 5


config = Config()
