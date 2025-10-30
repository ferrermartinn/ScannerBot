import sys
sys.path.insert(0, "/app")
from app.service.scanner_p2p import binance_p2p_query

def extract(item):
    adv  = (item.get("adv") or item) or {}
    advr = (item.get("advertiser") or {})
    price = adv.get("price") or adv.get("floatPrice") or item.get("price")
    nick  = advr.get("nickName") or advr.get("nickname") or item.get("nickName") or "-"
    return nick, price

def build_side(side):
    advs = binance_p2p_query("USDT", side, "ARS", [])
    rows = []
    for it in advs:
        nick, price = extract(it)
        if price is None: 
            continue
        rows.append({"nickName": nick, "price": float(price)})
    return rows

b = build_side("BUY")
s = build_side("SELL")
print("manual buyers/sellers:", len(b), len(s))
if b[:1]: print("buyers[0]:", b[0])
if s[:1]: print("sellers[0]:", s[0])