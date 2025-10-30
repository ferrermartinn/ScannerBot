import sys, os, time
sys.path.insert(0, "/app")
from app.service.scanner_p2p import build_asset_view, load_config, DATA_FILE, ASSETS, safe_write_json

while True:
    try:
        cfg = load_config()
        assets = {a: build_asset_view(a, cfg) for a in ASSETS}
        payload = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "fiat": cfg.get("fiat","ARS"), "assets": assets}
        safe_write_json(DATA_FILE, payload)
        print("tick data.json OK", payload["timestamp"], flush=True)
    except Exception as e:
        print("writer error:", e, flush=True)
    time.sleep(15)