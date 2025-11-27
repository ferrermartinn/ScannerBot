from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

INJECT = """
def _apply_my_suggest(info: dict, cfg: dict):
    try:
        b = float((info.get("competitor_buy")  or {}).get("price"))
        s = float((info.get("competitor_sell") or {}).get("price"))
        tick = float(cfg.get("price_delta_abs", 0.01))
        info["my_suggest_buy"]  = round(b + tick, 2)
        info["my_suggest_sell"] = round(s - tick, 2)
    except Exception:
        pass
"""

if "_apply_my_suggest(" not in s:
    s = s.replace("def fmt_price", INJECT + "\n\ndef fmt_price")

s = s.replace("header_asset(asset, spread)\n        render_blocks(info)",
              "header_asset(asset, spread)\n        _apply_my_suggest(info, load_config())\n        render_blocks(info)")
s = s.replace("header_asset(asset, spread)\n        render_blocks(info)\n        row = st.columns([1,3,3,3])",
              "header_asset(asset, spread)\n        _apply_my_suggest(info, load_config())\n        render_blocks(info)\n        row = st.columns([1,3,3,3])")

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: dashboard aplica my_suggest")