"""
backend/scripts/check_setup.py

Phase 1 checkpoint. Verifies Mongo, the LLM, and the MCA/data.gov.in config
are all wired up correctly before building agents on top of them.

Run from the project root: python -m backend.scripts.check_setup
"""
from backend.config import settings
from backend.database.connection import ping
from backend.utils.llm import get_llm


def check_mongo():
    print("Checking MongoDB Atlas connection...", end=" ")
    if ping():
        print("OK ✔")
    else:
        print("FAILED ✘ (check MONGO_URI in .env)")


def check_llm():
    print("Checking LLM connection...", end=" ")
    try:
        llm = get_llm()
        response = llm.call("Reply with exactly one word: OK")
        print(f"OK ✔ (model replied: {response.strip()!r})")
    except Exception as e:
        print(f"FAILED ✘ ({e})")


def check_mca_config():
    print("Checking MCA/data.gov.in config...", end=" ")
    if not settings.DATA_GOV_API_KEY:
        print("FAILED ✘ (DATA_GOV_API_KEY not set)")
    elif not settings.MCA_RESOURCE_IDS:
        print("FAILED ✘ (MCA_RESOURCE_IDS not set — find this on data.gov.in's catalog page)")
    else:
        print(f"OK ✔ ({len(settings.MCA_RESOURCE_IDS)} resource ID(s) configured)")
    print("  (this only checks config is present — run backend.scripts.probe_mca to test the real API)")


def main():
    print("=" * 40)
    print("JobShield AI — Phase 1 setup check")
    print("=" * 40)
    settings.validate()
    check_mongo()
    check_llm()
    check_mca_config()
    print("=" * 40)
    print("Phase 1 complete. Ready to test the MCA API with backend.scripts.probe_mca.")


if __name__ == "__main__":
    main()
