from pathlib import Path
import sys, py_compile, statistics

SRC = Path("/app/app/service/scanner_p2p.py")

INJECT = r"""
# === injected robust helpers ===
def _median_top(prices, n=3):
    vals = [p for p in prices if isinstance(p,(int,float))]
    vals.sort()
    take = vals[:max(1, min(n, len(vals)))]
    try:
        return statistics.median(take)
    except Exception:
        return take[0] if take else None
"""

REWRITE = r"""
def build_asset_view(asset: str, cfg: dict) -> dict:
    fiat = cfg.get("fiat", "ARS")
    pay_types = cfg.get("pay_types") or []

    try:
        buy_raw  = binance_p2p_query(asset, "BUY",  fiat, [])   # sin filtro duro
        sell_raw = binance_p2p_query(asset, "SELL", fiat, [])   # sin filtro duro
    except Exception as e:
        log.warning(f"[build_asset_view] query error: {e}")
        buy_raw, sell_raw = [], []

    # filtro suave por texto
    buy_raw  = [it for it in buy_raw  if _passes_pay_filter(it, pay_types)]
    sell_raw = [it for it in sell_raw if _passes_pay_filter(it, pay_types)]

    # extractor
    extractor = globals().get("_extract_price_nick", _extract_price_nick_fallback)

    buyers_table, sellers_table = [], []
    for it in buy_raw:
        try:
            price, nick = extractor(it)
        except Exception:
            price, nick = _extract_price_nick_fallback(it)
        if price is not None:
            buyers_table.append({"nickName": nick, "price": float(price)})

    for it in sell_raw:
        try:
            price, nick = extractor(it)
        except Exception:
            price, nick = _extract_price_nick_fallback(it)
        if price is not None:
            sellers_table.append({"nickName": nick, "price": float(price)})

    buyers_table  = sorted(buyers_table,  key=lambda x: x["price"])
    sellers_table = sorted(sellers_table, key=lambda x: x["price"])

    # robust top-of-book: mediana del top-3
    b_med = _median_top([x["price"] for x in buyers_table], n=3)
    s_med = _median_top([x["price"] for x in sellers_table], n=3)

    competitor_buy  = buyers_table[0]  if buyers_table  else {"nickName": "-", "price": None}
    competitor_sell = sellers_table[0] if sellers_table else {"nickName": "-", "price": None}

    # spread con guardas
    spread_percent = None
    if b_med and s_med and b_med > 0:
        sp = (s_med - b_med) / b_med * 100.0
        if -10.0 <= sp <= 10.0:   # descarta outliers
            spread_percent = sp

    tick = float(cfg.get("tick", 0.01) or 0.01)
    buy_undercut  = bool(cfg.get("buy_undercut", True))
    sell_overcut  = bool(cfg.get("sell_overcut", True))

    my_buy_hint  = round(b_med - tick if b_med is not None and buy_undercut else (b_med + tick if b_med is not None else 0), 2) if b_med is not None else None
    my_sell_hint = round(s_med + tick if s_med is not None and sell_overcut else (s_med - tick if s_med is not None else 0), 2) if s_med is not None else None

    return {
        "asset": asset,
        "competitor_buy":  competitor_buy,
        "competitor_sell": competitor_sell,
        "buyers_table": buyers_table,
        "sellers_table": sellers_table,
        "spread_percent": spread_percent,
        "my_buy_hint":  my_buy_hint,
        "my_sell_hint": my_sell_hint,
        "meta": {
            "buy_count": len(buyers_table),
            "sell_count": len(sellers_table),
            "b_med": b_med, "s_med": s_med
        }
    }
"""

def patch(t:str)->str:
    t = t.replace("\r\n","\n").replace("\r","\n")
    if "_median_top(" not in t:
        lines = t.splitlines()
        last_imp = 0
        for i,ln in enumerate(lines):
            s = ln.strip()
            if s.startswith("import ") or s.startswith("from "):
                last_imp = i
            elif last_imp and s and not s.startswith("#"):
                break
        lines.insert(last_imp+1, INJECT.strip())
        t = "\n".join(lines)

    start = t.find("\ndef build_asset_view(")
    if start == -1: start = t.find("def build_asset_view(")
    if start == -1:
        print("ERROR: no encontré def build_asset_view"); sys.exit(1)
    next_def = t.find("\ndef ", start+1)
    next_cls = t.find("\nclass ", start+1)
    end = min([c for c in (next_def, next_cls) if c != -1], default=len(t))
    return t[:start] + "\n" + REWRITE.strip() + t[end:]

s = SRC.read_text(encoding="utf-8")
s2 = patch(s)
tmp = SRC.with_suffix(".tmp.py")
tmp.write_text(s2, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(SRC)
print("OK: robust spread (median top-3) + guardas activado")