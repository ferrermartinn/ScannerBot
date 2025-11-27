from pathlib import Path
import re, py_compile

P = Path("/app/app/service/scanner_p2p.py")
s = P.read_text(encoding="utf-8")

# --- helper a inyectar (sin docstrings) ---
INJECT_HELPER = r"""
# === injected: pricing hints ===
def _round2(x):
    try:
        return float(f"{float(x):.2f}")
    except Exception:
        return None
"""

if "def _round2(" not in s:
    lines = s.splitlines()
    last_imp = 0
    for i, ln in enumerate(lines):
        t = ln.strip()
        if t.startswith("import ") or t.startswith("from "):
            last_imp = i
        elif last_imp and t and not t.startswith("#"):
            break
    lines.insert(last_imp+1, INJECT_HELPER.strip())
    s = "\n".join(lines)

# --- localizar build_asset_view y su return ---
m_fun = re.search(r"\ndef\s+build_asset_view\s*\([^)]*\):", s)
if not m_fun:
    raise SystemExit("No encontré build_asset_view(...)")

# buscar el 'return VAR' con indent 4 dentro de la función
m_ret = re.search(r"\n\s{4}return\s+([A-Za-z_][A-Za-z0-9_]*)\s*\n", s[m_fun.start():])
if not m_ret:
    raise SystemExit("No encontré 'return var' en build_asset_view")

retvar = m_ret.group(1)

# offset absoluto del final de la línea de return
ret_abs_start = m_fun.start() + m_ret.start()
ret_abs_end   = m_fun.start() + m_ret.end()

# código a insertar antes del return
INJECT_BEFORE_RETURN = f"""
    # injected: compute pricing hints based on top of book
    try:
        __m = {retvar}.setdefault('meta', {})
        top_buy  = __m.get('buy_top_price')  or __m.get('top_buy')  or __m.get('best_buy')
        top_sell = __m.get('sell_top_price') or __m.get('top_sell') or __m.get('best_sell')
        tick_b = (cfg.get('tick_buy')  or 0.01)
        tick_s = (cfg.get('tick_sell') or 0.01)
        mb = _round2((top_buy  or 0) + tick_b)
        ms = _round2((top_sell or 0) - tick_s)
        __m['my_buy_hint']  = mb
        __m['my_sell_hint'] = ms
    except Exception:
        pass
"""

# inyectar justo antes del return
s = s[:ret_abs_start] + "\n" + INJECT_BEFORE_RETURN + s[ret_abs_start:]

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: build_asset_view ahora calcula my_buy_hint / my_sell_hint")