"""
Centralized configuration. Everything else in the app imports from here
instead of calling os.getenv() directly, so there's exactly one place
that knows about environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM (provider-agnostic — same pattern as FitCrew AI)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    # MongoDB Atlas
    MONGO_URI: str = os.getenv("MONGO_URI", "")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "jobshield_ai")

    # data.gov.in Open Government Data API (MCA Company Master Data)
    # Note: named DATA_GOV_API_KEY (not DATA_GOV_IN_API_KEY) to match
    # tools/registry/mca_lookup_tool.py.
    DATA_GOV_API_KEY: str = os.getenv("DATA_GOV_API_KEY", "")
    DATA_GOV_BASE_URL: str = os.getenv(
        "DATA_GOV_BASE_URL",
        "https://www.data.gov.in/backend/dataapi/v1/resource",
    )

    # Comma-separated resource IDs of the "Company Master Data" dataset(s).
    # data.gov.in may publish one resource per RoC, so this is a list.
    MCA_RESOURCE_IDS: list = [
        r.strip() for r in os.getenv("MCA_RESOURCE_IDS", "").split(",") if r.strip()
    ]

    # API field names used for server-side filters. Verify with
    # backend/scripts/probe_mca.py and override in .env if the dataset uses
    # different names.
    MCA_NAME_FIELD: str = os.getenv("MCA_NAME_FIELD", "company_name")
    MCA_CIN_FIELD: str = os.getenv("MCA_CIN_FIELD", "cin")
    MCA_TIMEOUT_SECONDS: int = int(os.getenv("MCA_TIMEOUT_SECONDS", "20"))

    @classmethod
    def validate(cls):
        missing = []
        if not cls.MONGO_URI:
            missing.append("MONGO_URI")
        if not cls.DATA_GOV_API_KEY:
            missing.append("DATA_GOV_API_KEY")
        if not cls.MCA_RESOURCE_IDS:
            missing.append("MCA_RESOURCE_IDS")

        if cls.LLM_MODEL.startswith("gemini/") and not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        elif cls.LLM_MODEL.startswith("openrouter/") and not cls.OPENROUTER_API_KEY:
            missing.append("OPENROUTER_API_KEY")
        elif cls.LLM_MODEL.startswith("openai/") and not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")

        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill these in."
            )


settings = Settings()
