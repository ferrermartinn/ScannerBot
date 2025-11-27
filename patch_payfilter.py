from pathlib import Path
import sys, json, py_compile

SRC = Path("/app/app/service/scanner_p2p.py")

INJECT = r"""
# === injected pay-method helpers ===
def _passes_pay_filter(item: dict, pay_types):
    # Si no hay filtros, pasa todo
    if not pay_types:
        return True
    # Texto plano con todo el anuncio para búsquedas robustas
    try:
        blob = json.dumps(item, ensure_ascii=False).lower()
    except Exception:
        return True
    # normalizo agujas
    needles = [str(x).lower() for x in pay_types if x]
    # match si aparece cualquiera de las agujas
    return any(n in blob for n in needles)
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

    buyers_table, sellers_table = [], []
    for it in buy_raw:
        price, nick = _extract_price_nick(it)
        if price is not None:
            buyers_table.append({"nickName": nick, "price": price})

    for it in sell_raw:
        price, nick = _extract_price_nick(it)
        if price is not None:
            sellers_table.append({"nickName": nick, "price": price})

    buyers_table  = sorted(buyers_table,  key=lambda x: x["price"])
    sellers_table = sorted(sellers_table, key=lambda x: x["price"])

    competitor_buy  = buyers_table[0]  if buyers_table  else {"nickName": "-", "price": None}
    competitor_sell = sellers_table[0] if sellers_table else {"nickName": "-", "price": None}

    bprice = competitor_buy.get("price")
    sprice = competitor_sell.get("price")

    spread_percent = None
    if bprice is not None and sprice is not None and bprice > 0:
        spread_percent = (sprice - bprice) / bprice * 100.0

    tick = float(cfg.get("tick", 0.01) or 0.01)
    buy_undercut  = bool(cfg.get("buy_undercut", True))
    sell_overcut  = bool(cfg.get("sell_overcut", True))

    my_buy_hint  = round(bprice - tick if bprice is not None and buy_undercut else (bprice + tick if bprice is not None else 0), 2) if bprice is not None else None
    my_sell_hint = round(sprice + tick if sprice is not None and sell_overcut else (sprice - tick if sprice is not None else 0), 2) if sprice is not None else None

    return {
        "asset": asset,
        "competitor_buy":  competitor_buy,
        "competitor_sell": competitor_sell,
        "buyers_table": buyers_table,
        "sellers_table": sellers_table,
        "spread_percent": spread_percent,
        "my_buy_hint":  my_buy_hint,
        "my_sell_hint": my_sell_hint,
    }
"""

def patch(text: str) -> str:
    t = text.replace("\r\n","\n").replace("\r","\n")
    if "_passes_pay_filter(" not in t:
        # insertar INJECT tras los imports
        lines = t.splitlines()
        last_imp = 0
        for i, ln in enumerate(lines):
            s = ln.strip()
            if s.startswith("import ") or s.startswith("from "):
                last_imp = i
            elif last_imp and s and not s.startswith("#"):
                break
        lines.insert(last_imp+1, INJECT.strip())
        t = "\n".join(lines)

    # sustituir implementación de build_asset_view
    start = t.find("\ndef build_asset_view(")
    if start == -1:
        start = t.find("def build_asset_view(")
    if start == -1:
        print("ERROR: no encontré def build_asset_view")
        sys.exit(1)
    next_def = t.find("\ndef ", start+1)
    next_cls = t.find("\nclass ", start+1)
    end = min([c for c in [next_def, next_cls] if c != -1], default=len(t))
    t = t[:start] + "\n" + REWRITE.strip() + t[end:]
    return t

def main():
    s = SRC.read_text(encoding="utf-8")
    s2 = patch(s)
    tmp = SRC.with_suffix(".tmp.py")
    tmp.write_text(s2, encoding="utf-8")
    py_compile.compile(str(tmp), doraise=True)
    tmp.replace(SRC)
    print("OK: soft pay filter injected")
if __name__ == "__main__":
    main()