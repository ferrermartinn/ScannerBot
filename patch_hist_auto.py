from pathlib import Path
import py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

HELPER = '''
def _append_history_snapshot():
    """Agrega una fila por activo al archivo historico_spreads_v2.json."""
    import json, os, time
    DATA = os.path.join(DATA_DIR, "data.json")
    HIST = os.path.join(DATA_DIR, "historico_spreads_v2.json")

    # lee estado actual
    try:
        d = json.load(open(DATA, "r", encoding="utf-8"))
    except Exception:
        return
    assets = (d.get("assets") or {})
    ts = d.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for a, v in assets.items():
        sp = v.get("spread_percent") or v.get("spread_pct")
        try:
            if isinstance(sp, str):
                sp = float(str(sp).replace("%",""))
            if isinstance(sp, (int, float)):
                rows.append({"datetime": ts, "asset": a, "spread": float(sp)})
        except Exception:
            pass

    # carga lo existente y agrega
    try:
        hist = json.load(open(HIST, "r", encoding="utf-8"))
        if not isinstance(hist, list):
            hist = []
    except Exception:
        hist = []
    hist = [x for x in hist if isinstance(x, dict)] + rows
    hist = hist[-5000:]  # límite
    tmp = HIST + ".tmp"
    open(tmp, "w", encoding="utf-8").write(json.dumps(hist, ensure_ascii=False, indent=2))
    os.replace(tmp, HIST)
'''

# 1) insertar helper si no existe
if "_append_history_last_minutes(" in s:
    pass  # no usado; seguridad
if "_append_history_snapshot(" not in s:
    s = s.replace("def load_history_last_minutes", HELPER + "\n\ndef load_history_last_minutes", 1)

# 2) llamar al helper antes de dibujar el histórico
s = s.replace(
    "st.divider()\n    render_history(seconds_window=1800)",
    "st.divider()\n    _append_history_snapshot()\n    render_history(seconds_window=1800)"
)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: histórico auto-append activado")