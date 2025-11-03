from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

INJECT = """
def _to_f(x, d=None):
    try: return float(str(x).replace(",", ""))
    except: return d

def _round2(x):
    try: return float(f"{float(x):.2f}")
    except: return None

def _pick_first8_from_tables(info: dict):
    buyers = list((info or {}).get("buyers_table")  or [])[:8]
    sellers= list((info or {}).get("sellers_table") or [])[:8]
    cb = max(buyers,  key=lambda r: _to_f((r or {}).get("price"), 0.0)) if buyers  else None
    cs = min(sellers, key=lambda r: _to_f((r or {}).get("price"), 1e18)) if sellers else None
    return cb, cs

def _recalc_competitors_and_hints(info: dict, cfg: dict):
    # 1) elegir top-8 actuales
    cb, cs = _pick_first8_from_tables(info)
    if cb: info["competitor_buy"]  = cb
    if cs: info["competitor_sell"] = cs

    # 2) tick mixto: max(Δabs, precio×Δ%)
    try:
        d_abs = float((cfg or {}).get("price_delta_abs", 0.01))
    except Exception:
        d_abs = 0.01
    try:
        d_pct = float((cfg or {}).get("price_delta_pct", 0.0)) / 100.0
    except Exception:
        d_pct = 0.0

    pb = _to_f((cb or {}).get("price"))
    ps = _to_f((cs or {}).get("price"))

    db = max(d_abs, (pb or 0.0) * d_pct) if pb is not None else None
    ds = max(d_abs, (ps or 0.0) * d_pct) if ps is not None else None

    buy_hint  = _round2((pb + db) if (pb is not None and db is not None) else None)
    sell_hint = _round2((ps - ds) if (ps is not None and ds is not None) else None)

    if buy_hint  is not None: info["my_suggest_buy"]  = buy_hint
    if sell_hint is not None: info["my_suggest_sell"] = sell_hint

def _normalize_asset_for_ui(info: dict, cfg: dict):
    try:
        _recalc_competitors_and_hints(info, cfg)
    except Exception:
        pass
    return info
"""

# 1) inyectar helpers si no existen
if "_normalize_asset_for_ui" not in s:
    s = s.replace("def card_compact(asset: str, info: dict):", INJECT + "\n\ndef card_compact(asset: str, info: dict):", 1)

# 2) normalizar antes de renderizar tarjetas en sección "Operar"
s = s.replace(
    "if pinned and pinned in ASSETS and assets.get(pinned):\n        card_expanded(pinned, assets[pinned])",
    "if pinned and pinned in ASSETS and assets.get(pinned):\n        assets[pinned] = _normalize_asset_for_ui(assets.get(pinned) or {}, cfg)\n        card_expanded(pinned, assets[pinned])"
)

s = s.replace(
    "for i, a in enumerate(ASSETS):\n            with cols[i % 2]:\n                card_compact(a, assets.get(a) or {})",
    "for i, a in enumerate(ASSETS):\n            with cols[i % 2]:\n                assets[a] = _normalize_asset_for_ui(assets.get(a) or {}, cfg)\n                card_compact(a, assets.get(a) or {})"
)

s = s.replace(
    "for i, a in enumerate(others):\n                with cols[i % (3 if compact_others else 2)]:\n                    card_compact(a, assets.get(a) or {})",
    "for i, a in enumerate(others):\n                with cols[i % (3 if compact_others else 2)]:\n                    assets[a] = _normalize_asset_for_ui(assets.get(a) or {}, cfg)\n                    card_compact(a, assets.get(a) or {})"
)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: normalizador Top-8 + tick mixto activo en dashboard")