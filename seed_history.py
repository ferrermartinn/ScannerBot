from pathlib import Path
import json, os, time

DATA = Path("/app/data/data.json")
HIST = Path("/app/data/historico_spreads.json")

def rjson(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

d = rjson(DATA, {})
assets = (d.get("assets") or {})
ts = d.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")

# filas nuevas a partir del snapshot actual
new_rows = []
for a, v in assets.items():
    sp = v.get("spread_percent")
    if isinstance(sp, (int, float)):
        new_rows.append({"datetime": ts, "asset": a, "spread": float(sp)})

# merge con lo existente si era lista
old = rjson(HIST, [])
if isinstance(old, list):
    rows = [r for r in old if isinstance(r, dict)] + new_rows
else:
    rows = new_rows

# limitar a los últimos 2000 puntos para no crecer infinito
rows = rows[-2000:]

tmp = HIST.with_suffix(".tmp")
tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, HIST)
print(f"seeded rows={len(new_rows)} total={len(rows)}")