import sys; sys.path.insert(0, "/app")
from app.service.scanner_p2p import binance_p2p_query
for side in ("BUY","SELL"):
    advs = binance_p2p_query("USDT", side, "ARS", [])
    print(side, "len:", len(advs), "keys0:", list((advs[0] if advs else {}).keys())[:2])