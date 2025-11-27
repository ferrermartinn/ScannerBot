# -*- coding: utf-8 -*-
"""
scanner_p2p.py — v2.6
- Loop garantizado
- Headers P2P por .env
- Escrituras a DATA_DIR (/app/data)
- Archivos: data.json, historico_spreads.json, historico_snapshots.json, state.json
"""

import os, json, time, logging, requests
from datetime import datetime
from collections import deque
from typing import List, Dict, Any, Optional
# === injected helpers (pay filter + extractor fallback) ===
import json
from app.service.effective_liquidity import effective_metrics
from app.strategy.triangular_arbitrage import calculate_triangular_arbitrage
from app.strategy.triangular_arbitrage import fetch_spot_btcusdt






def _passes_pay_filter(item: dict, pay_types):
    if not pay_types:
        return True
    try:
        blob = json.dumps(item, ensure_ascii=False).lower()
    except Exception:
        return True
    needles = [str(x).lower() for x in pay_types if x]
    return any(n in blob for n in needles)

def _extract_price_nick_fallback(item: dict):
    # Binance P2P típico: {"adv": {...,"price": "1488.00"}, "advertiser": {"nickName": "X"}}
    price = None
    nick  = "-"
    try:
        adv = item.get("adv") or {}
        p = adv.get("price") or adv.get("advPrice") or adv.get("priceFloat")
        if isinstance(p, str):
            p = p.replace(",", "").strip()
        price = float(p) if p not in (None, "", "-") else None
    except Exception:
        price = None
    try:
        nick = (item.get("advertiser") or {}).get("nickName") or adv.get("sellerNickName") or "-"
    except Exception:
        nick = "-"
    return price, nick
# === injected pay-method helpers ===
def _passes_pay_filter(item: dict, pay_types):
    # Si no hay filtros, pasa todo
    if not pay_types:
        return True
    # Texto plano con todo el anuncio para búsquedas robustas
    try:
        blob = json.dumps(item, ensure_ascii=False).lower()
    except Exception:
        return True
    # normalizo agujas
    needles = [str(x).lower() for x in pay_types if x]
    # match si aparece cualquiera de las agujas
    return any(n in blob for n in needles)

# ====== ENV / PATHS ======
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)
logging.getLogger("urllib3").setLevel(logging.WARNING)


CONFIG_FILE          = os.path.join(DATA_DIR, "config.json")
DATA_FILE            = os.path.join(DATA_DIR, "data.json")
HISTORICO_FILE       = os.path.join(DATA_DIR, "historico_spreads.json")
HISTORICO_SNAP_FILE  = os.path.join(DATA_DIR, "historico_snapshots.json")
STATE_FILE           = os.path.join(DATA_DIR, "state.json")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger("scanner_p2p")

# ====== CONFIG ======
DEFAULT_CONFIG = { "spread_use_effective": True,
    "verified_only": False,
    "paused": False,
    "mute_alerts": True,
    "fiat": "ARS",
    "scan_interval_sec": 10,
    "margins": {"USDT": 0.01, "BTC": 100.0, "ETH": 50.0, "XRP": 1.0},  # EPS en precio absoluto
    "pay_types": [],
    "alert_spread_pct": 1.0,
    "alert_spread_pct_by_asset": {},
    "alert_min_ars": 1500.0,
    "alert_min_ars_by_asset": {},
    "trade_costs": {"taker_fee_pct": 0.10, "slippage_pct": 0.05},
    "blacklist": [],
    "allow_sim": True,
    "positioning": {"window_s": 60, "dumping_drop_pct": 0.006, "debounce_s": 45},
}

ASSETS = ["USDT", "BTC", "ETH", "XRP"]

# ====== HEADERS / P2P ======
BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
ENV_HEADERS = {
    "Content-Type": os.getenv("P2P_CONTENT_TYPE", "application/json"),
    "User-Agent":   os.getenv("P2P_USER_AGENT",   "Mozilla/5.0"),
    "clienttype":   os.getenv("P2P_CLIENTTYPE",   "web"),
    "platform":     os.getenv("P2P_PLATFORM",     "web"),
}
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Origin": "https://p2p.binance.com",
    "Referer": "https://p2p.binance.com/",
}
HEADERS = {**DEFAULT_HEADERS, **ENV_HEADERS}

# ====== IO helpers ======
def safe_read_json(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def safe_write_json(path: str, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def deepmerge(base: dict, defaults: dict) -> dict:
    out = dict(base) if isinstance(base, dict) else {}
    for k, v in defaults.items():
        if isinstance(v, dict):
            out[k] = deepmerge(out.get(k, {}), v)
        else:
            out.setdefault(k, v)
    return out

def load_config() -> dict:
    cfg_disk = safe_read_json(CONFIG_FILE, {}) or {}
    cfg = deepmerge(cfg_disk, DEFAULT_CONFIG)
    safe_write_json(CONFIG_FILE, cfg)
    return cfg

# ====== Normalización ======
def _pick(*vals, default=None):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return default

def _as_float(x) -> Optional[float]:
    try:
        if isinstance(x, str) and x.endswith("%"):
            x = x[:-1]
        return float(x)
    except Exception:
        return None

def norm_name(ad: dict) -> str:
    adv = (ad or {}).get("advertiser") or (ad or {}).get("advertiserVo") or {}
    return _pick(
        adv.get("nickName"), adv.get("userName"),
        (ad or {}).get("nickName"), (ad or {}).get("advertiserName"),
        (ad or {}).get("username"), (ad or {}).get("name"),
        (ad or {}).get("title"), (ad or {}).get("label"), default="-",
    )

def norm_price(ad: dict) -> Optional[float]:
    adv = (ad or {}).get("adv") or {}
    return _as_float(_pick(adv.get("price"), (ad or {}).get("price"),
                           (ad or {}).get("floatPrice"), (ad or {}).get("amount")))

def norm_row(ad: dict) -> dict:
    adv = (ad or {}).get("adv") or {}
    methods = (adv.get("tradeMethods") or (ad or {}).get("tradeMethods") or [])
    if methods and isinstance(methods[0], dict):
        methods = [m.get("identifier") or m.get("name") or m.get("payType") or "?" for m in methods]
    return {
        "nickName": norm_name(ad),
        "price": norm_price(ad),
        "minAmount": _as_float(_pick(adv.get("minSingleTransAmount"), (ad or {}).get("minAmount"))),
        "totalAmount": _as_float(_pick(adv.get("tradableQuantity"), (ad or {}).get("totalAmount"))),
        "methods": methods,
    }

def get_margin(asset: str, cfg: dict) -> float:
    try:
        return float((cfg.get("margins") or {}).get(asset, 0.01))
    except Exception:
        return 0.01

def is_blacklisted_name(name: Optional[str], cfg: dict) -> bool:
    if not name:
        return False
    name_l = str(name).lower()
    bl = [str(s).strip().lower() for s in (cfg.get("blacklist") or []) if str(s).strip()]
    return any(pat in name_l or name_l == pat for pat in bl)

def is_verified_ad(ad: dict) -> bool:
    try:
        advr = (ad or {}).get("advertiser") or (ad or {}).get("advertiserVo") or {}
        tags = set()
        for k in ("tagList", "userTags", "tags"):
            v = advr.get(k) or []
            if isinstance(v, (list, tuple)):
                tags.update([str(x).lower() for x in v])
            elif isinstance(v, str):
                tags.add(v.lower())
        user_type = str(advr.get("userType") or "").lower()
        flags = [
            advr.get("merchantCheck") is True,
            advr.get("isMerchant") is True,
            user_type == "merchant",
            "merchant" in tags or "verified_merchant" in tags or "verified" in tags,
        ]
        return any(flags)
    except Exception:
        return False

# ====== Binance P2P ======
def binance_p2p_query(asset: str, trade_type: str, fiat: str, pay_types: List[str]) -> List[dict]:
    payload = {
        "asset": asset, "tradeType": trade_type, "fiat": fiat,
        "page": 1, "rows": 20, "payTypes": pay_types or [], "publisherType": None
    }
    try:
        r = requests.post(BINANCE_P2P_URL, headers=HEADERS, json=payload, timeout=15)
        r.raise_for_status()
        return (r.json() or {}).get("data") or []
    except Exception as e:
        log.warning(f"[P2P] Falla consulta {asset}/{trade_type}: {e}")
        return []

# ====== Precios top por asset/fiat usando P2P ======
def get_market_prices(asset: str, fiat: str, pay_types: list) -> tuple[float | None, float | None]:
    """
    Retorna (top_buy_price, top_sell_price) del libro P2P para `asset` contra `fiat`.
    - top_buy_price: mejor precio del lado BUY (compradores de crypto)
    - top_sell_price: mejor precio del lado SELL (vendedores de crypto)
    """
    def _top_price(rows):
        # intenta extraer precio con _extractor si existe, si no usa el fallback
        extractor = globals().get("_extract_price_nick", _extract_price_nick_fallback)
        prices = []
        for it in rows or []:
            try:
                p, _ = extractor(it)
            except Exception:
                p, _ = _extract_price_nick_fallback(it)
            if p is not None:
                prices.append(float(p))
        return min(prices) if prices else None

    try:
        buy_raw  = binance_p2p_query(asset, "BUY",  fiat, pay_types or [])
        sell_raw = binance_p2p_query(asset, "SELL", fiat, pay_types or [])
        top_buy  = _top_price(buy_raw)
        top_sell = _top_price(sell_raw)
        return top_buy, top_sell
    except Exception as e:
        log.warning(f"[get_market_prices] {asset}/{fiat} error: {e}")
        return None, None


# ====== Simulador ======
def sim_rows(asset: str, side: str, n: int = 10) -> List[dict]:
    import random
    base = {"USDT": 1325, "BTC": 15500000, "ETH": 5900000, "XRP": 4206}
    b = base.get(asset, 1000)
    rows = []
    for i in range(n):
        price = round(b + (8 if side == "SELL" else 0) + random.uniform(-5, 5), 2)
        rows.append({
            "adv": {"price": str(price), "minSingleTransAmount": "10", "tradableQuantity": "1000",
                    "tradeMethods": [{"identifier": "MP"}]},
            "advertiser": {"nickName": f"(sim){side.lower()}_{i:02d}"},
        })
    return rows

# ====== Sonidos (silenciado por defecto) ======
def play_sound(kind: str, cfg: dict):
    if cfg.get("mute_alerts", True):
        return
    try:
        import sonidos
        keymap = {"oportunidad":"alerta_rentable","precio":"alerta_precio","caida":"alerta_caida","vibrido":"alerta_vibrido"}
        vol = float((cfg.get("vol_sounds") or {}).get(keymap.get(kind, "alerta_rentable"), 0.5))
        sonidos.play(kind, volume=vol)
    except Exception:
        pass

# ====== Asset view ======
def build_asset_view(asset: str, cfg: dict) -> dict:
    fiat = cfg.get("fiat", "ARS")
    pay_types = cfg.get("pay_types") or []

    try:
        buy_raw  = binance_p2p_query(asset, "BUY",  fiat, [])   # sin filtro duro
        sell_raw = binance_p2p_query(asset, "SELL", fiat, [])   # sin filtro duro
    except Exception as e:
        log.warning(f"[build_asset_view] query error: {e}")
        buy_raw, sell_raw = [], []

    # filtro suave por texto
    buy_raw  = [it for it in buy_raw  if _passes_pay_filter(it, pay_types)]
    sell_raw = [it for it in sell_raw if _passes_pay_filter(it, pay_types)]

    # elegir extractor disponible
    extractor = globals().get("_extract_price_nick", _extract_price_nick_fallback)

    

    buyers_table, sellers_table = [], []
    for it in buy_raw:
        try:
            price, nick = extractor(it)
        except Exception:
            price, nick = _extract_price_nick_fallback(it)
        if price is not None:
            buyers_table.append({"nickName": nick, "price": price})

    for it in sell_raw:
        try:
            price, nick = extractor(it)
        except Exception:
            price, nick = _extract_price_nick_fallback(it)
        if price is not None:
            sellers_table.append({"nickName": nick, "price": price})
    
    

    buyers_table  = sorted(buyers_table,  key=lambda x: x["price"])
    sellers_table = sorted(sellers_table, key=lambda x: x["price"])

    competitor_buy  = buyers_table[0]  if buyers_table  else {"nickName": "-", "price": None}
    competitor_sell = sellers_table[0] if sellers_table else {"nickName": "-", "price": None}

    bprice = competitor_buy.get("price")
    sprice = competitor_sell.get("price")

    spread_percent = None
    if bprice is not None and sprice is not None and bprice > 0:
        spread_percent = (sprice - bprice) / bprice * 100.0

    tick = float(cfg.get("tick", 0.01) or 0.01)
    buy_undercut  = bool(cfg.get("buy_undercut", True))
    sell_overcut  = bool(cfg.get("sell_overcut", True))

    my_buy_hint  = round(bprice - tick if bprice is not None and buy_undercut else (bprice + tick if bprice is not None else 0), 2) if bprice is not None else None
    my_sell_hint = round(sprice + tick if sprice is not None and sell_overcut else (sprice - tick if sprice is not None else 0), 2) if sprice is not None else None



    eff_buy, eff_sell, eff_mid, eff_spread = effective_metrics(buyers_table, sellers_table, cfg.get("alert_min_ars", 1500.0))
    sr = f"{spread_percent:.3f}%" if spread_percent is not None else "NA"
    se = f"{eff_spread:.3f}%" if eff_spread is not None else "NA"
    log.info("[P2P] spread_raw=%s  effective=%s  use_effective=%s", sr, se, cfg.get('spread_use_effective', True))
log.info("[P2P] spread_raw=%s  effective=%s  use_effective=%s", sr, se, cfg.get('spread_use_effective', True))
