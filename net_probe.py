import sys, json, requests
url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}
payload = {
    "asset": "USDT", "tradeType": "BUY", "fiat": "ARS",
    "page": 1, "rows": 20, "payTypes": [], "publisherType": None
}
r = requests.post(url, headers=headers, json=payload, timeout=15)
print("status", r.status_code)
try:
    d = r.json()
    # muestrita del shape
    data = d.get("data")
    if isinstance(data, dict):
        advs = data.get("advList") or data.get("data") or []
    else:
        advs = data or []
    print("len", len(advs))
    if advs[:1]:
        print("keys0", list(advs[0].keys())[:8])
except Exception as e:
    print("JSON error:", e, "text[:200]=", r.text[:200])