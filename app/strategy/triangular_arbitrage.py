# app/strategy/triangular_arbitrage.py
import logging
from typing import Tuple

log = logging.getLogger("triangular_arbitrage")

def calculate_triangular_arbitrage(
    ars_to_usdt: Tuple[float, float],
    usdt_to_btc: Tuple[float, float],
    btc_to_ars: Tuple[float, float],
) -> Tuple[bool, float, float]:
    """
    Calcula si existe oportunidad de arbitraje triangular.
    Retorna (hay_oportunidad, ganancia_pct, monto_final_ars) para 1 ARS inicial.
    """
    buy_ars_to_usdt  = float(ars_to_usdt[0])   # ARS -> USDT (precio de compra)
    sell_usdt_to_btc = float(usdt_to_btc[1])   # USDT -> BTC (precio de venta)
    buy_btc_to_ars   = float(btc_to_ars[0])    # BTC  -> ARS (precio de compra)

    amount_in_ars = 1.0
    amount_in_usdt = amount_in_ars * buy_ars_to_usdt
    amount_in_btc  = amount_in_usdt * sell_usdt_to_btc
    amount_out_ars = amount_in_btc * buy_btc_to_ars

    if amount_out_ars > amount_in_ars:
        profit_pct = (amount_out_ars - amount_in_ars) / amount_in_ars * 100.0
        return True, profit_pct, amount_out_ars
    return False, 0.0, amount_out_ars

# --- spot BTC/USDT desde Binance REST (ligero) ---
def fetch_spot_btcusdt() -> float | None:
    """
    Devuelve el precio spot BTC/USDT (float) o None si falla.
    """
    import requests
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=3.5)
        r.raise_for_status()
        data = r.json()  # {'symbol':'BTCUSDT','price':'67000.12'}
        return float(data.get("price"))
    except Exception:
        return None
