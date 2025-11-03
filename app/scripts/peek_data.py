# -*- coding: utf-8 -*-
import json
from pathlib import Path

DATA = Path("/app/data/data.json")

def short(v):
    if isinstance(v, list): return f"list[{len(v)}]"
    if isinstance(v, dict): return f"dict({len(v.keys())} keys)"
    return type(v).__name__

def peek_sample(lst):
    if not isinstance(lst, list) or not lst: return None
    x = lst[0]
    if isinstance(x, dict):
        adv = x.get("adv") or {}
        return {"top_keys": list(x.keys())[:8],
                "adv_keys": list(adv.keys())[:12] if isinstance(adv, dict) else None}
    return str(type(x))

def main():
    try:
        obj = json.loads(DATA.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[err] no pude leer {DATA}: {e}")
        return 1
    assets = obj.get("assets") or {}
    print(f"[info] fiat={obj.get('fiat')} timestamp={obj.get('timestamp')}")
    for sym, blob in assets.items():
        print(f"\n=== {sym} ===")
        if not isinstance(blob, dict):
            print(f"  tipo asset={type(blob)}"); continue
        for k, v in blob.items():
            print(f"  {k}: {short(v)}")
        for bkey, skey in [("buys","sells"), ("buy","sell"), ("bids","asks"),
                           ("raw_buys","raw_sells"), ("buy_ads","sell_ads"),
                           ("compras","ventas")]:
            buys, sells = blob.get(bkey), blob.get(skey)
            if isinstance(buys, list) and isinstance(sells, list):
                print(f"  -> candidato libros: {bkey}/{skey}")
                print(f"     sample buys: {peek_sample(buys)}")
                print(f"     sample sells: {peek_sample(sells)}")
                break
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
