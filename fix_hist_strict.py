from pathlib import Path
import json, os, time

DATA = Path("/app/data/data.json")
HIST = Path("/app/data/historico_spreads.json")

def rjson(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

# 1) Tomo snapshot actual
d = rjson(DATA, {})
assets = d.get("assets") or {}
ts = d.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")

rows = []
for a, v in assets.items():
    sp = v.get("spread_percent")
    if isinstance(sp, (int, float)):
        rows.append({"datetime": ts, "asset": a, "spread": float(sp)})

# 2) Si el histórico NO es list[dict], lo reemplazo por filas válidas
raw = rjson(HIST, [])
if not isinstance(raw, list) or not all(isinstance(x, dict) for x in raw):
    new_hist = rows
else:
    # ya es lista: conservo y agrego las nuevas filas
    new_hist = [x for x in raw if isinstance(x, dict)] + rows

# 3) Cap de 2000 filas y escritura
new_hist = new_hist[-2000:]
tmp = HIST.with_suffix(".tmp")
tmp.write_text(json.dumps(new_hist, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, HIST)
print("hist_rows=", len(new_hist))