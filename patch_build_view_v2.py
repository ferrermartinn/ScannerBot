from pathlib import Path
import sys, py_compile

SRC = Path("/app/app/service/scanner_p2p.py")

HELPER = (
"""def _extract_price_nick(item):
    adv  = (item.get("adv") or item) or {}
    advr = (item.get("advertiser") or {})
    price = adv.get("price") or adv.get("floatPrice") or item.get("price")
    nick  = (advr.get("nickName") or advr.get("nickname") or item.get("nickName") or "-")
    try:
        price = float(price) if price is not None else None
    except Exception:
        price = None
    return price, nick
"""
)

NEW_BUILD = (
"""def build_asset_view(asset: str, cfg: dict) -> dict:
    fiat = cfg.get("fiat", "ARS")
    pay_types = cfg.get("pay_types")  # puede ser None o lista

    def q(side, ptypes):
        return binance_p2p_query(asset, side, fiat, ptypes or [])

    try:
        buy_raw  = q("BUY",  pay_types)
        sell_raw = q("SELL", pay_types)
        # fallback si el filtro por pay_types vacía resultados
        if not buy_raw and pay_types:  buy_raw  = q("BUY",  [])
        if not sell_raw and pay_types: sell_raw = q("SELL", [])
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

    # Orden: menor precio primero en ambos (ajustá si tu UI espera otra cosa)
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
"""
)

def ensure_typing_imports(txt: str) -> str:
    need_list = "from typing import List" not in txt
    need_dict = "from typing import Dict" not in txt
    if not (need_list or need_dict):
        return txt
    lines = txt.splitlines()
    ins = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            ins = i
        elif ins >= 0:
            break
    add = []
    if need_list: add.append("from typing import List")
    if need_dict: add.append("from typing import Dict")
    lines[ins+1:ins+1] = add
    return "\n".join(lines)

def insert_helper_if_missing(txt: str) -> str:
    if "_extract_price_nick(" in txt:
        return txt
    # Insertar antes de la def build_asset_view si existe; si no, tras imports
    pos = txt.find("\ndef build_asset_view(")
    if pos == -1:
        pos = txt.find("def build_asset_view(")
    if pos != -1:
        return txt[:pos] + "\n\n" + HELPER + "\n" + txt[pos:]
    # fallback: tras bloque de imports
    lines = txt.splitlines()
    ins = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            ins = i
        elif ins >= 0:
            break
    if ins == -1:
        return HELPER + "\n\n" + txt
    lines.insert(ins+1, "")
    lines.insert(ins+2, HELPER.rstrip())
    return "\n".join(lines)

def replace_build_asset_view(txt: str) -> str:
    # localizar inicio exacto de la función (preferimos en columna 0)
    start = txt.find("\ndef build_asset_view(")
    offset = 1
    if start == -1:
        start = txt.find("def build_asset_view(")
        offset = 0
    if start == -1:
        print("ERROR: no encontré def build_asset_view(")
        sys.exit(1)
    start += offset

    # fin: siguiente "\ndef " o "\nclass " o EOF
    next_def = txt.find("\ndef ", start+1)
    next_cls = txt.find("\nclass ", start+1)
    candidates = [c for c in [next_def, next_cls, len(txt)] if c != -1]
    end = min(candidates) if candidates else len(txt)

    prefix = txt[:start]
    suffix = txt[end:]
    if not prefix.endswith("\n\n"): prefix = prefix.rstrip() + "\n\n"
    if not suffix.startswith("\n"): suffix = "\n" + suffix
    return prefix + NEW_BUILD + suffix

def main():
    s = SRC.read_text(encoding="utf-8")
    s = s.replace("\r\n","\n").replace("\r","\n").replace("\t","    ")
    s = s.replace("\u00A0", " ").replace("\u200B", "")
    s = ensure_typing_imports(s)
    s = insert_helper_if_missing(s)
    s = replace_build_asset_view(s)
    tmp = SRC.with_suffix(".tmp.py")
    tmp.write_text(s, encoding="utf-8")
    py_compile.compile(str(tmp), doraise=True)
    tmp.replace(SRC)
    print("OK: build_asset_view reemplazada + helper insertado + py_compile OK")

if __name__ == "__main__":
    main()