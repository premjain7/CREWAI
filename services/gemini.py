"""Gemini LLM configuration service for CrewAI."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")


def get_gemini_api_key() -> str:
    """Retrieve Gemini API key from environment."""
    key = os.getenv("GEMINI_API_KEY")
    if not key or key.strip() == "" or key == "your_gemini_api_key_here":
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your environment or .env file."
        )
    return key.strip()


def get_llm(
    temperature: float = 0.2,
    max_tokens: Optional[int] = 4096,
    model: Optional[str] = None,
):
    """Factory to create a CrewAI LLM instance configured for Gemini.

    Avoids initializing real LLMs during import time.
    """
    from crewai import LLM

    api_key = get_gemini_api_key()
    selected_model = model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    kwargs = {
        "model": selected_model,
        "api_key": api_key,
        "temperature": temperature,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    return LLM(**kwargs)
