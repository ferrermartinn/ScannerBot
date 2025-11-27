from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

# --- 1) Inserta helper si no existe ---
HELP = """
def _apply_my_suggest(info: dict, cfg: dict):
    \"\"\"Regla maker:
        Mi Compra = top_buy + 0.01
        Mi Venta  = top_sell - 0.01
        Donde top_* vienen de competitor_* .price
    \"\"\"
    try:
        b = float((info.get("competitor_buy")  or {}).get("price"))
        s_ = float((info.get("competitor_sell") or {}).get("price"))
        tick = float((load_config() or {}).get("price_delta_abs", 0.01))
        info["my_suggest_buy"]  = round(b + tick, 2)
        info["my_suggest_sell"] = round(s_ - tick, 2)
    except Exception:
        # Si falta algún dato, no rompe la UI
        pass
"""

if "_apply_my_suggest(" not in s:
    # Inserta el helper antes de fmt_price
    s = s.replace("def fmt_price", HELP + "\n\ndef fmt_price", 1)

# --- 2) Llamar al helper antes de renderizar tarjetas ---
# card_compact
s = s.replace(
    "header_asset(asset, spread)\n        render_blocks(info)",
    "header_asset(asset, spread)\n        _apply_my_suggest(info, load_config())\n        render_blocks(info)"
)

# card_expanded
s = s.replace(
    "header_asset(asset, spread)\n        render_blocks(info)\n        row = st.columns([1,3,3,3])",
    "header_asset(asset, spread)\n        _apply_my_suggest(info, load_config())\n        render_blocks(info)\n        row = st.columns([1,3,3,3])"
)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: _apply_my_suggest aplicado y llamado en tarjetas")