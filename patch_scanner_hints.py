from pathlib import Path
import re, py_compile

P = Path("/app/app/service/scanner_p2p.py")
s = P.read_text(encoding="utf-8")

# helper simple para redondear a 2 decimales
if "def _round2(" not in s:
    s = s.replace("\nfrom ", "\n# === injected: pricing helpers ===\n"
                     "def _round2(x):\n"
                     "    try:\n"
                     "        return float(f\"{float(x):.2f}\")\n"
                     "    except Exception:\n"
                     "        return None\n\nfrom ", 1)

m_fun = re.search(r"\ndef\s+build_asset_view\s*\([^)]*\):", s)
if not m_fun:
    raise SystemExit("no build_asset_view")

m_ret = re.search(r"\n\s{4}return\s+([A-Za-z_][A-Za-z0-9_]*)\s*\n", s[m_fun.start():])
if not m_ret:
    raise SystemExit("no return var in build_asset_view")

retvar = m_ret.group(1)
ret_abs_start = m_fun.start() + m_ret.start()

# f-string con llaves literales escapadas {{ }}
INJECT = f"""
    # injected: compute pricing hints based on top of book
    try:
        __m = {retvar}.setdefault('meta', {{}})
        top_buy  = __m.get('buy_top_price')  or __m.get('top_buy')  or __m.get('best_buy')
        top_sell = __m.get('sell_top_price') or __m.get('top_sell') or __m.get('best_sell')
        tick_b = (cfg.get('tick_buy')  or 0.01)
        tick_s = (cfg.get('tick_sell') or 0.01)
        __m['my_buy_hint']  = _round2((top_buy  or 0) + tick_b)
        __m['my_sell_hint'] = _round2((top_sell or 0) - tick_s)
    except Exception:
        pass
"""

s = s[:ret_abs_start] + "\n" + INJECT + s[ret_abs_start:]

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: pricing hints")