from pathlib import Path
import re as _re
import py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

NEW = """
def _apply_my_suggest(info: dict, cfg: dict):
    try:
        b = float((info.get("competitor_buy")  or {}).get("price"))
        s = float((info.get("competitor_sell") or {}).get("price"))
        d_abs = float(cfg.get("price_delta_abs", 0.01))
        d_pct = float(cfg.get("price_delta_pct", 0.0)) / 100.0
        db = max(d_abs, b * d_pct)
        ds = max(d_abs, s * d_pct)
        info["my_suggest_buy"]  = round(b + db, 2)
        info["my_suggest_sell"] = round(s - ds, 2)
    except Exception:
        pass
"""
s = _re.sub(r"def _apply_my_suggest\(info: dict, cfg: dict\):[\s\S]*?^\s*def fmt_price",
            NEW + "\n\ndef fmt_price", s, flags=_re.M)

tmp = P.with_suffix(".tmp"); tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True); tmp.replace(P)
print("OK: tick mixto activado")