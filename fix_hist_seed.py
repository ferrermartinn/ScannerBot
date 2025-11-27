from pathlib import Path
import json, time, os

DATA = Path("/app/data/data.json")
HIST = Path("/app/data/historico_spreads.json")

def rj(p, d):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except: return d

d = rj(DATA, {})
assets = (d.get("assets") or {})
ts = d.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")

rows = []
for a, v in assets.items():
    sp = v.get("spread_percent") or v.get("spread_pct")
    if isinstance(sp, (int, float)):
        rows.append({"datetime": ts, "asset": a, "spread": float(sp)})

raw = rj(HIST, [])
if not isinstance(raw, list): raw = []
raw = [x for x in raw if isinstance(x, dict)] + rows
raw = raw[-2000:]

tmp = HIST.with_suffix(".tmp")
tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, HIST)
print("hist_rows=", len(raw))