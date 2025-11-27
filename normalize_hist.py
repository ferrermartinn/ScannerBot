from pathlib import Path
import json, os

H = Path("/app/data/historico_spreads.json")

def _read(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

raw = _read(H)
rows = []

# aceptar varios formatos: list | {rows|data|items|history: [...]}
if isinstance(raw, list):
    rows = [r for r in raw if isinstance(r, dict)]
elif isinstance(raw, dict):
    for k in ("rows","data","items","history"):
        v = raw.get(k)
        if isinstance(v, list):
            rows = [r for r in v if isinstance(r, dict)]
            break

# sólo conservar campos útiles si existen
norm = []
for r in rows:
    d = {}
    if "datetime" in r: d["datetime"] = r["datetime"]
    if "asset" in r:    d["asset"]    = r["asset"]
    if "spread" in r:   d["spread"]   = r["spread"]
    if d: norm.append(d)

tmp = H.with_suffix(".tmp")
tmp.write_text(json.dumps(norm, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, H)
print(f"normalized_ok rows={len(norm)}")