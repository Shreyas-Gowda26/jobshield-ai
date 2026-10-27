"""
Standalone check for the MCA integration. Run from the project root:

    python -m backend.scripts.probe_mca "Infosys Limited" "Some Tiny Startup Pvt Ltd" "Zzqx Fake Traders"
    python -m backend.scripts.probe_mca --cin L85110KA1981PLC013115

Step 1 prints raw field names per resource so you can fix MCA_NAME_FIELD / aliases.
"""
import json
import sys

from backend.config import settings
from backend.tools.registry import mca_lookup_tool as mca


def show_schema():
    print("== Schema probe ==")
    for rid in settings.MCA_RESOURCE_IDS:
        try:
            recs = mca._query(rid, {}, limit=2)
        except mca.MCAApiError as e:
            print(f"{rid}: ERROR {e}")
            continue
        print(f"{rid}: {len(recs)} sample record(s)")
        if recs:
            print("  fields:", list(recs[0].keys()))
            print("  sample:", json.dumps(recs[0], indent=2)[:800])


def main(args):
    show_schema()
    if args and args[0] == "--cin":
        result = mca.lookup_cin(args[1])
        print("\n== CIN lookup ==")
        print(json.dumps({k: v for k, v in result.items() if k != "matches"}, indent=2, default=str))
        for m in result["matches"]:
            print({k: v for k, v in m.items() if k != "raw"})
        return
    for name in args:
        result = mca.lookup_company(name)
        print(f"\n== {name} -> {result['status']} (tried: {result['tried']}) ==")
        for e in result["errors"]:
            print("  error:", e)
        for m in result["matches"][:3]:
            print("  ", {k: v for k, v in m.items() if k != "raw"})


if __name__ == "__main__":
    main(sys.argv[1:])
