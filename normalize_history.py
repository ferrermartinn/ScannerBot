from pathlib import Path
import json, re, os, sys, py_compile

# 1) localizar la ruta real del histórico desde dashboard.py (constante HIST_FILE)
DP = Path("/app/app/ui/dashboard.py")
code = DP.read_text(encoding="utf-8")

# Busca patrones: HIST_FILE = Path("...")  o  HIST_FILE = "..."
m = re.search(r'HIST_FILE\s*=\s*Path\((["\'])(.*?)\1\)', code)
hist_path = None
if m:
    hist_path = m.group(2)
else:
    m2 = re.search(r'HIST_FILE\s*=\s*(["\'])(.*?)\1', code)
    if m2:
        hist_path = m2.group(2)

if not hist_path:
    print("ERR: no encontré HIST_FILE en dashboard.py")
    sys.exit(1)

H = Path(hist_path)
if not H.is_absolute():
    H = Path("/app")/hist_path

# 2) leer y normalizar: debe quedar una lista de dicts
def _read_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

raw = _read_json(H)
rows = []

if isinstance(raw, list):
    rows = [r for r in raw if isinstance(r, dict)]
elif isinstance(raw, dict):
    for key in ("rows","data","items","history"):
        v = raw.get(key)
        if isinstance(v, list):
            rows = [r for r in v if isinstance(r, dict)]
            break
# si nada sirve, dejar lista vacía
if rows is None:
    rows = []

# 3) escribir normalizado
tmp = H.with_suffix(".tmp")
tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, H)

print(f"OK: normalized {H} rows={len(rows)}")