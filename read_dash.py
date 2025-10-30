import json, os
p="/app/data/data.json"
d=json.load(open(p,"r",encoding="utf-8"))
u=d["assets"]["USDT"]
print("DASH rows:", len(u.get("buyers_table") or []), len(u.get("sellers_table") or []))
print("DASH top buy/sell:", (u.get("competitor_buy") or {}), (u.get("competitor_sell") or {}))