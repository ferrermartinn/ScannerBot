# -*- coding: utf-8 -*-
from typing import Iterable, Optional, Tuple

def _to_float(x) -> Optional[float]:
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        s = str(x).strip().replace(",", "")
        return float(s)
    except Exception:
        return None

def _get(d: dict, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict): return None
        cur = cur.get(k)
    return cur

def extract_price(ad: dict) -> Optional[float]:
    # price en raíz, o dentro de adv.*, o dentro de nested dicts comunes
    for path in [
        ("price",),
        ("adv","price"),
        ("data","price"),
        ("offer","price"),
    ]:
        v = _to_float(_get(ad, *path))
        if v and v > 0: return v
    return None

def extract_fiat_capacity(ad: dict) -> Optional[float]:
    # Primero campos FIAT directos
    for path in [
        ("adv","dynamicMaxSingleTransAmount"),
        ("adv","maxSingleTransAmount"),
        ("dynamicMaxSingleTransAmount",),
        ("maxSingleTransAmount",),
    ]:
        v = _to_float(_get(ad, *path))
        if v and v > 0: return v
    # Proxy: qty_base * price
    price = extract_price(ad)
    if price and price > 0:
        for path in [
            ("adv","tradableQuantity"),
            ("adv","surplusAmount"),
            ("adv","availableAmount"),
            ("adv","available"),
            ("adv","amount"),
            ("tradableQuantity",),
            ("surplusAmount",),
            ("availableAmount",),
            ("available",),
            ("amount",),
        ]:
            q = _to_float(_get(ad, *path))
            if q and q > 0: return q * price
    # Último recurso: minSingleTransAmount
    for path in [
        ("adv","minSingleTransAmount"),
        ("minSingleTransAmount",),
    ]:
        v = _to_float(_get(ad, *path))
        if v and v > 0: return v
    return None

def effective_price(quotes: Iterable[dict], min_fiat: float) -> Optional[float]:
    if not quotes: return None
    need = float(min_fiat)
    if need <= 0: return None
    filled = 0.0; cost = 0.0
    for ad in quotes:
        price = extract_price(ad)
        cap   = extract_fiat_capacity(ad)
        if not price or price <= 0 or not cap or cap <= 0: continue
        take = min(cap, need - filled)
        if take <= 0: break
        cost += take * price
        filled += take
        if filled >= need: break
    if filled <= 0: return None
    return cost / filled

def effective_metrics(buys, sells, min_fiat: float) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    # Yo compro cripto → tomo vendedores (sells). Yo vendo cripto → tomo compradores (buys).
    eff_buy  = effective_price(sells, min_fiat)
    eff_sell = effective_price(buys,  min_fiat)
    if eff_buy is None or eff_sell is None: return eff_buy, eff_sell, None, None
    eff_mid = (eff_buy + eff_sell) / 2.0
    eff_spread_pct = ((eff_sell - eff_buy) / eff_mid) * 100.0 if eff_mid else None
    return eff_buy, eff_sell, eff_mid, eff_spread_pct
