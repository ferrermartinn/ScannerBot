import sys, os, time
sys.path.insert(0, "/app")
from app.service.scanner_p2p import build_asset_view, load_config, DATA_FILE, ASSETS, safe_write_json

cfg = load_config()
assets = {a: build_asset_view(a, cfg) for a in ASSETS}
payload = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "fiat": cfg.get("fiat","ARS"), "assets": assets}
safe_write_json(DATA_FILE, payload)

u = assets.get("USDT", {}) or {}
print("SMOKE rows:", len(u.get("buyers_table") or []), len(u.get("sellers_table") or []))
print("SMOKE top buy/sell:", (u.get("competitor_buy") or {}), (u.get("competitor_sell") or {}))