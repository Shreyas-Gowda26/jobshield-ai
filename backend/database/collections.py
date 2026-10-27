"""
database/collections.py

Single source of truth for MongoDB collection names.
"""

COMPANY_CHECKS = "company_checks"      # cached MCA/WHOIS/search lookups per company
VERIFICATION_HISTORY = "verification_history"  # full verdicts (score + red flags) over time
