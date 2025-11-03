from pathlib import Path
import sys, time, json, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

INJECT = r'''
# === injected: robust data loader ===
import time, json, streamlit as st
from pathlib import Path

_DATA = Path("/app/data/data.json")

def _safe_read_json(max_tries: int = 3, delay: float = 0.15):
    for _ in range(max_tries):
        try:
            with _DATA.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            time.sleep(delay)
    return None

def _view_defaults(v: dict) -> dict:
    v = v or {}
    v.setdefault("competitor_buy",  {"nickName": "-", "price": None})
    v.setdefault("competitor_sell", {"nickName": "-", "price": None})
    v.setdefault("spread_percent",  None)
    v.setdefault("my_buy_hint",     None)
    v.setdefault("my_sell_hint",    None)
    v.setdefault("meta", {})
    v["meta"].setdefault("buy_count", 0)
    v["meta"].setdefault("sell_count", 0)
    v["meta"].setdefault("b_med", None)
    v["meta"].setdefault("s_med", None)
    return v

def load_views_or_fallback():
    # Lee data.json con reintentos; si falla, usa la última muestra buena
    data = _safe_read_json()
    now = time.time()

    if data and isinstance(data, dict):
        ts_ok = True
        try:
            import datetime as _dt
            t = _dt.datetime.strptime(data.get("timestamp","1970-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
            ts_ok = (now - t.timestamp()) < 20
        except Exception:
            ts_ok = True

        if ts_ok and "assets" in data:
            views = {a: _view_defaults(v) for a, v in data["assets"].items()}
            st.session_state["_last_good_views"] = views
            return views

    return st.session_state.get("_last_good_views", {})
'''

# 1) Inyecta helpers si faltan
if "def load_views_or_fallback()" not in s:
    lines = s.splitlines()
    last_imp = 0
    for i, ln in enumerate(lines):
        t = ln.strip()
        if t.startswith("import ") or t.startswith("from "):
            last_imp = i
        elif last_imp and t and not t.startswith("#"):
            break
    lines.insert(last_imp+1, INJECT.strip())
    s = "\n".join(lines)

# 2) Reemplaza lecturas directas del JSON por el loader robusto
s = s.replace("json.load(open('/app/data/data.json'))", "load_views_or_fallback()")
s = s.replace('json.load(open("/app/data/data.json"))', "load_views_or_fallback()")

# 3) Asegura helper para mostrar spread n/a si falta
if "_fmt_spread(" not in s:
    s += "\n# injected: spread helper label\ndef _fmt_spread(x):\n    return 'n/a' if x is None else f\"{x:.2f}%\"\n"

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: dashboard con lectura robusta y fallbacks")