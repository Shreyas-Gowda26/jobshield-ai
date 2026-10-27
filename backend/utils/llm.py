"""
utils/llm.py

Provider-agnostic LLM factory (same pattern as FitCrew AI). Switching
providers is just an .env change:

    Gemini (default):
        LLM_MODEL=gemini/gemini-2.5-flash
        GEMINI_API_KEY=...

    OpenAI:
        LLM_MODEL=openai/gpt-4o-mini
        OPENAI_API_KEY=...

    OpenRouter:
        LLM_MODEL=openrouter/<provider>/<model>
        OPENROUTER_API_KEY=...
"""
from crewai import LLM

from backend.config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_llm(temperature: float = 0.7) -> LLM:
    model = settings.LLM_MODEL
    kwargs = {"model": model, "temperature": temperature}

    if model.startswith("gemini/"):
        kwargs["api_key"] = settings.GEMINI_API_KEY
    elif model.startswith("openrouter/"):
        kwargs["api_key"] = settings.OPENROUTER_API_KEY
        kwargs["base_url"] = OPENROUTER_BASE_URL
    elif model.startswith("openai/"):
        kwargs["api_key"] = settings.OPENAI_API_KEY

    return LLM(**kwargs)
