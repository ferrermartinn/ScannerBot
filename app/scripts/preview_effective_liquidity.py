# -*- coding: utf-8 -*-
import json, os, sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
from app.service.effective_liquidity import effective_metrics

DATA_IN  = Path("/app/data/data.json")
DATA_OUT = Path("/app/data/data_effective.json")

PAIR_KEYS = [
    ("buyers_table","sellers_table"),
    ("buys","sells"), ("buy","sell"), ("bids","asks"),
    ("raw_buys","raw_sells"), ("buy_ads","sell_ads"),
    ("compras","ventas"),
]

def safe_load(p: Path) -> Dict[str, Any]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[warn] no pude leer {p}: {e}")
        return {}

def find_books(blob: Dict[str, Any]) -> Tuple[Iterable[dict], Iterable[dict], str]:
    for bkey, skey in PAIR_KEYS:
        buys, sells = blob.get(bkey), blob.get(skey)
        if isinstance(buys, list) and isinstance(sells, list):
            return buys, sells, f"{bkey}/{skey}"
    return None, None, ""

def main(min_fiat: float):
    src = safe_load(DATA_IN)
    if not src:
        print("[warn] data.json vacío o ilegible.")
        return 1
    out = {"fiat": src.get("fiat"), "timestamp": src.get("timestamp"), "assets": {}}
    assets = src.get("assets") or {}
    total = 0; ok = 0
    for sym, blob in assets.items():
        total += 1
        if not isinstance(blob, dict):
            print(f"[info] {sym}: asset no-dict (saltando)")
            continue
        buys, sells, pair = find_books(blob)
        if buys is None:
            print(f"[info] {sym}: sin listas de libros compatibles (saltando)")
            continue
        eff_buy, eff_sell, eff_mid, eff_sp = effective_metrics(buys, sells, min_fiat)
        out["assets"][sym] = {
            "pair_keys": pair,
            "effective_buy_price": eff_buy,
            "effective_sell_price": eff_sell,
            "effective_mid": eff_mid,
            "effective_spread_percent": eff_sp,
        }
        ok += 1
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    with DATA_OUT.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] activos procesados {ok}/{total}. Output: {DATA_OUT}")
    return 0

if __name__ == "__main__":
    try:
        min_fiat = float(os.environ.get("MIN_FIAT", "150000"))
        if len(sys.argv) >= 2:
            min_fiat = float(sys.argv[1])
    except Exception:
        min_fiat = 150000.0
    sys.exit(main(min_fiat))
