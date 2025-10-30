import sys, json
sys.path.insert(0, "/app")

from app.service.scanner_p2p import binance_p2p_query

try:
    advs_buy  = binance_p2p_query("USDT","BUY","ARS",[])
    advs_sell = binance_p2p_query("USDT","SELL","ARS",[])
    print("P2P probe -> BUY len:", len(advs_buy), "| SELL len:", len(advs_sell))
    # Muestra 1 ejemplo crudo para ver el shape
    def peek(sample):
        if not sample: return
        a = sample[0]
        adv  = (a.get("adv") or {})
        advr = (a.get("advertiser") or {})
        price = adv.get("price") or a.get("price")
        nick  = advr.get("nickName") or advr.get("nickname") or a.get("nickName")
        print("sample keys:", list(a.keys())[:8])
        print("sample price/nick:", price, nick)
    peek(advs_buy)
except Exception as e:
    print("P2P probe ERROR:", e)