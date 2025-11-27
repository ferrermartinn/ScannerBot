# -*- coding: utf-8 -*-
import json
from pathlib import Path
DATA = Path("/app/data/data.json")
def main():
    obj = json.loads(DATA.read_text(encoding="utf-8"))
    assets = obj.get("assets") or {}
    for sym, blob in assets.items():
        bt = blob.get("buyers_table"); st = blob.get("sellers_table")
        if isinstance(bt, list) and bt:
            print(f"\n=== {sym} buyers_table[0] ===\n{json.dumps(bt[0], ensure_ascii=False, indent=2)}")
        if isinstance(st, list) and st:
            print(f"\n=== {sym} sellers_table[0] ===\n{json.dumps(st[0], ensure_ascii=False, indent=2)}")
        break
if __name__ == "__main__":
    main()
