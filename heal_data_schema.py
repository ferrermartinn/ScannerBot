from pathlib import Path
import json, os, tempfile, time

P = Path("/app/data/data.json")

def _view_defaults(v: dict) -> dict:
    v = v or {}
    v.setdefault("competitor_buy",  {"nickName":"-","price":None})
    v.setdefault("competitor_sell", {"nickName":"-","price":None})
    v.setdefault("spread_percent",  None)
    v.setdefault("my_buy_hint",     None)
    v.setdefault("my_sell_hint",    None)
    m = v.setdefault("meta", {})
    m.setdefault("buy_count",0); m.setdefault("sell_count",0)
    m.setdefault("b_med",None);   m.setdefault("s_med",None)
    return v

d = {}
try:
    d = json.loads(P.read_text(encoding="utf-8"))
except Exception:
    d = {}

assets = d.get("assets") or {}
for a, v in list(assets.items()):
    assets[a] = _view_defaults(v)
d["assets"] = assets

# marca de esquema para rastreo
d["schema_ver"] = 2
d.setdefault("fiat","ARS")

tmp = P.with_suffix(".tmp")
tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(tmp, P)
print("healed + schema_ver=2")