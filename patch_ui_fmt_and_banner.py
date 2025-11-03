from pathlib import Path, re
p = Path("/app/app/ui/dashboard.py"); s = p.read_text(encoding="utf-8")

# 1) helper de formato si no existe
if "_fmt_spread(" not in s:
    s += "\n# injected: spread helper label\ndef _fmt_spread(x):\n    return 'n/a' if x is None else f\"{x:.2f}%\"\n"

# 2) reemplazos conservadores de usos típicos del spread por el helper
s = re.sub(r"round\\(\\s*view\\.get\\('spread_percent'\\)\\s*or\\s*0\\s*,\\s*2\\s*\\)",
           "_fmt_spread(view.get('spread_percent'))", s)
s = s.replace("f\"{view.get('spread_percent'):.2f}%\"",
              "_fmt_spread(view.get('spread_percent'))")

# 3) banner superior con ts y edad del archivo
if "# injected: data banner" not in s:
    banner = """
# injected: data banner
try:
    _raw = _safe_read_json()
    _ts = _raw.get("timestamp") if isinstance(_raw, dict) else None
    import datetime as _dt, time as _t
    _age = None
    if _ts:
        _dt_ts = _dt.datetime.strptime(_ts, "%Y-%m-%d %H:%M:%S")
        _age = int(_t.time() - _dt_ts.timestamp())
    if _ts:
        st.caption(f"data.json actualizado: {_ts}  |  edad: {_age}s")
except Exception:
    pass
"""
    s += banner

p.write_text(s, encoding="utf-8")
print("OK: spread n/a + banner timestamp")