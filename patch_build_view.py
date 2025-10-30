from pathlib import Path
import re, sys, py_compile

SRC = Path("/app/app/service/scanner_p2p.py")

HELPER = """
def _extract_price_nick(item):
    adv  = (item.get("adv") or item) or {}
    advr = (item.get("advertiser") or {})
    price = adv.get("price") or adv.get("floatPrice") or item.get("price")
    nick  = (advr.get("nickName") or advr.get("nickname") or
             item.get("nickName") or "-")
    try:
        price = float(price) if price is not None else None
    except Exception:
        price = None
    return price, nick
""".strip()+"\n\n"

NEW_BUILD = """
def build_asset_view(asset: str, cfg: dict) -> dict:
    # Requiere: binance_p2p_query(asset, trade_type, fiat, pay_types)
    fiat = cfg.get("fiat", "ARS")
    pay_types = cfg.get("pay_types") or []

    try:
        buy_raw  = binance_p2p_query(asset, "BUY",  fiat, pay_types)
        sell_raw = binance_p2p_query(asset, "SELL", fiat, pay_types)
    except Exception as e:
        log.warning(f"[build_asset_view] query error: {e}")
        buy_raw, sell_raw = [], []

    buyers_table = []
    for it in buy_raw:
        price, nick = _extract_price_nick(it)
        if price is None:
            continue
        buyers_table.append({"nickName": nick, "price": price})

    sellers_table = []
    for it in sell_raw:
        price, nick = _extract_price_nick(it)
        if price is None:
            continue
        sellers_table.append({"nickName": nick, "price": price})

    # Orden básico: BUY de menor a mayor precio (mejor comprador primero),
    # SELL de menor a mayor (mejor vendedor primero).
    buyers_table  = sorted(buyers_table, key=lambda x: x["price"])
    sellers_table = sorted(sellers_table, key=lambda x: x["price"])

    competitor_buy  = buyers_table[0]  if buyers_table  else {"nickName": "-", "price": None}
    competitor_sell = sellers_table[0] if sellers_table else {"nickName": "-", "price": None}

    return {
        "asset": asset,
        "competitor_buy":  competitor_buy,
        "competitor_sell": competitor_sell,
        "buyers_table": buyers_table,
        "sellers_table": sellers_table,
    }
""".strip()+"\n\n"

def ensure_imports(txt: str) -> str:
    # from typing import List (ya lo tenés) — añadimos Dict si no estuviera
    add = []
    if not re.search(r"^\\s*from\\s+typing\\s+import\\s+List\\b", txt, re.M):
        add.append("from typing import List")
    if not re.search(r"^\\s*from\\s+typing\\s+import\\s+Dict\\b", txt, re.M):
        add.append("from typing import Dict")
    if not add:
        return txt
    # insertar tras el primer bloque de imports
    lines = txt.splitlines()
    ins = 0
    for i, ln in enumerate(lines):
        if re.match(r'^\\s*(import|from)\\s+\\w+', ln):
            ins = i
        elif ins and not re.match(r'^\\s*(import|from)\\s+\\w+', ln):
            break
    for i, a in enumerate(add, start=1):
        lines.insert(ins+i, a)
    return "\\n".join(lines)

def insert_helper_if_missing(s: str) -> str:
    if "_extract_price_nick" in s:
        return s
    # Lo colocamos antes de build_asset_view si existe, o al final del bloque de imports
    m = re.search(r"^def\\s+build_asset_view\\s*\\(", s, re.M)
    if m:
        idx = m.start()
        return s[:idx] + HELPER + s[idx:]
    # fallback: tras imports
    lines = s.splitlines()
    ins = 0
    for i, ln in enumerate(lines):
        if re.match(r'^\\s*(import|from)\\s+\\w+', ln):
            ins = i
        elif ins and not re.match(r'^\\s*(import|from)\\s+\\w+', ln):
            break
    lines.insert(ins+1, HELPER.rstrip())
    return "\\n".join(lines)

def replace_build_asset_view(s: str) -> str:
    # Reemplazamos toda la función build_asset_view por NEW_BUILD
    m = re.search(r"^def\\s+build_asset_view\\s*\\([^)]*\\):", s, re.M)
    if not m:
        print("ERROR: no encontré def build_asset_view(")
        sys.exit(1)
    start = m.start()
    # fin = siguiente "def <algo>(" al inicio de línea, o EOF
    m2 = re.search(r"^def\\s+\\w+\\s*\\(", s[m.end():], re.M)
    end = (m.end()+m2.start()) if m2 else len(s)
    prefix = s[:start]
    suffix = s[end:]
    # Aseguramos doble línea en límites
    if not prefix.endswith("\\n\\n"):
        prefix = prefix.rstrip()+"\\n\\n"
    if not suffix.startswith("\\n"):
        suffix = "\\n"+suffix
    return prefix + NEW_BUILD + suffix

def main():
    s = SRC.read_text(encoding="utf-8")
    s = s.replace("\\r\\n","\\n").replace("\\r","\\n").replace("\\t","    ")
    s = s.replace("\\u00A0", " ").replace("\\u200B", "")

    s = ensure_imports(s)
    s = insert_helper_if_missing(s)
    s = replace_build_asset_view(s)

    tmp = SRC.with_suffix(".tmp.py")
    tmp.write_text(s, encoding="utf-8")
    py_compile.compile(str(tmp), doraise=True)
    tmp.replace(SRC)
    print("OK: build_asset_view reemplazada + helper insertado + py_compile OK")
if __name__ == "__main__":
    main()