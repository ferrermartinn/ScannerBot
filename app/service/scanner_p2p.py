# -*- coding: utf-8 -*-
"""
scanner_p2p.py — v2.5
- 'vibrido' (sonido leve) cuando perdemos TOP en compra/venta
- Umbral por activo, simulador opcional, blacklist, costos, histórico
- FIX: Mi Compra/Mi Venta ahora son PRECIOS DE AVISO para ganar el TOP
  * Mi Compra  = top_buyer + margen
  * Mi Venta   = top_seller - margen
  * Spread mostrado = (top_buyer / top_seller - 1) - costos
"""

import json
import os
import time
import logging
from collections import deque
from app.service.bandit.core import DeltaBandit
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

CONFIG_FILE = "config.json"
DATA_FILE = "data.json"
HISTORICO_FILE = "historico_spreads.json"
HISTORICO_SNAP_FILE = "historico_snapshots.json"
STATE_FILE = "state.json"

DEFAULT_CONFIG = {
    "verified_only": False,
    "paused": False,
    "mute_alerts": False,
    "fiat": "ARS",
    "scan_interval_sec": 5,
    "margins": {"USDT": 0.01, "BTC": 0.01, "ETH": 0.01, "XRP": 0.01},
    "pay_types": [],
    "alert_spread_pct": 1.0,                 # global
    "alert_spread_pct_by_asset": {},         # por activo
    "alert_min_ars": 1500.0,
    "alert_min_ars_by_asset": {},
    "trade_costs": {"taker_fee_pct": 0.10, "slippage_pct": 0.05},
    "blacklist": [],
    "allow_sim": True,
    "vol_sounds": {
        "alerta_caida": 0.5,
        "alerta_precio": 0.4,
        "alerta_rentable": 0.9,
        "alerta_vibrido": 0.2,               # vibrido suave
    },
}
ASSETS = ["USDT", "BTC", "ETH", "XRP"]

# ---------------- I/O ----------------
def safe_read_json(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def safe_write_json(path: str, payload):
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

# ---------------- Normalización ----------------
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
    adv = (ad or {}).get("advertiser") or {}
    return _pick(
        adv.get("nickName"),
        adv.get("userName"),
        (ad or {}).get("nickName"),
        (ad or {}).get("advertiserName"),
        (ad or {}).get("username"),
        (ad or {}).get("name"),
        (ad or {}).get("title"),
        (ad or {}).get("label"),
        default="-",
    )

def norm_price(ad: dict) -> Optional[float]:
    adv = (ad or {}).get("adv") or {}
    return _as_float(_pick(adv.get("price"),
                           (ad or {}).get("price"),
                           (ad or {}).get("floatPrice"),
                           (ad or {}).get("amount")))

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

# ---------------- Binance P2P ----------------
BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://p2p.binance.com",
    "Referer": "https://p2p.binance.com/",
    "User-Agent": "Mozilla/5.0",
}

def binance_p2p_query(asset: str, trade_type: str, fiat: str, pay_types: List[str]) -> List[dict]:
    payload = {
        "asset": asset,
        "tradeType": trade_type,
        "fiat": fiat,
        "page": 1,
        "rows": 20,
        "payTypes": pay_types or [],
        "publisherType": None
    }
    try:
        r = requests.post(BINANCE_P2P_URL, headers=DEFAULT_HEADERS, json=payload, timeout=10)
        r.raise_for_status()
        return (r.json() or {}).get("data") or []
    except Exception as e:
        logging.warning(f"[P2P] Falla consulta {asset}/{trade_type}: {e}")
        return []

# ---------------- Simulador opcional ----------------
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

# ---------------- Sonidos / estado ----------------
def load_state() -> dict:
    return safe_read_json(STATE_FILE, {}) or {}

def save_state(s: dict):
    safe_write_json(STATE_FILE, s)

def play_sound(kind: str, cfg: dict):
    if cfg.get("mute_alerts"):
        return
    keymap = {
        "oportunidad": "alerta_rentable",
        "precio": "alerta_precio",
        "caida": "alerta_caida",
        "vibrido": "alerta_vibrido",
    }
    vol_key = keymap.get(kind, "alerta_rentable")
    vol = (cfg.get("vol_sounds") or {}).get(vol_key, 0.5)
    try:
        import sonidos
        sonidos.play(kind, volume=float(vol))
    except Exception:
        pass

# ---------------- Armado por activo ----------------
def build_asset_view(asset: str, cfg: dict) -> dict:
    """
    FIX principal:
      - my_suggest_buy  = top buyer + eps  (te ponés por ENCIMA del mejor comprador, ganás el TOP de compra)
      - my_suggest_sell = top seller - eps (te ponés por DEBAJO del mejor vendedor, ganás el TOP de venta)
      - spread_percent  = (top_buyer / top_seller - 1) - costos
    """
    fiat = cfg.get("fiat", "ARS")
    pay_types = cfg.get("pay_types") or []
    allow_sim = bool(cfg.get("allow_sim", True))

    sellers_raw = binance_p2p_query(asset, "SELL", fiat, pay_types)
    buyers_raw  = binance_p2p_query(asset, "BUY",  fiat, pay_types)

    if not sellers_raw and allow_sim:
        sellers_raw = sim_rows(asset, "SELL")
    if not buyers_raw and allow_sim:
        buyers_raw  = sim_rows(asset, "BUY")

    # FILTER_VERIFIED
    if cfg.get("verified_only"):
        sellers_raw = [ad for ad in sellers_raw if is_verified_ad(ad)]
        buyers_raw  = [ad for ad in buyers_raw  if is_verified_ad(ad)]
    sellers_tab = [norm_row(ad) for ad in sellers_raw]
    buyers_tab  = [norm_row(ad) for ad in buyers_raw]
    sellers_tab = [r for r in sellers_tab if (r.get("price") is not None and not is_blacklisted_name(r.get("nickName"), cfg))]
    buyers_tab  = [r for r in buyers_tab  if (r.get("price") is not None and not is_blacklisted_name(r.get("nickName"), cfg))]

    sellers_table = sellers_tab[:10]
    buyers_table  = buyers_tab[:10]

    comp_sell = sellers_table[0] if sellers_table else {"nickName": "-", "price": None}  # mejor vendedor (menor precio)
    comp_buy  = buyers_table[0]  if buyers_table  else {"nickName": "-", "price": None}  # mejor comprador (mayor precio)

    eps = get_margin(asset, cfg)

    top_seller_price = comp_sell["price"] if comp_sell["price"] is not None else None
    top_buyer_price  = comp_buy["price"]  if comp_buy["price"]  is not None else None

    # NUEVO: Precios de AVISO para ganar el top
    my_ad_buy  = round(top_buyer_price + eps, 2) if top_buyer_price is not None else None
    my_ad_sell = round(top_seller_price - eps, 2) if top_seller_price is not None else None

    # Spread teórico del libro (mejor comprador vs mejor vendedor), menos costos
    spread_percent = None
    if top_seller_price and top_buyer_price and top_seller_price > 0:
        gross = (top_buyer_price / top_seller_price - 1.0) * 100.0
        tc = cfg.get("trade_costs", {}) or {}
        costs = float(tc.get("taker_fee_pct", 0.0)) + float(tc.get("slippage_pct", 0.0))
        spread_percent = round(gross - costs, 2)

    return {
        "competitor_buy":  {"nickName": comp_buy["nickName"],  "price": top_buyer_price},
        "competitor_sell": {"nickName": comp_sell["nickName"], "price": top_seller_price},
        "my_suggest_buy":  my_ad_buy,     # AVISO de COMPRA (para ganar top)
        "my_suggest_sell": my_ad_sell,    # AVISO de VENTA  (para ganar top)
        "spread_percent":  spread_percent,
        "sellers_table":   sellers_table,
        "buyers_table":    buyers_table,
    }

# ---------------- Histórico ----------------
def append_history_flat(assets_out: Dict[str, Any]):
    hist = safe_read_json(HISTORICO_FILE, [])
    if not isinstance(hist, list):
        hist = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for asset, v in assets_out.items():
        hist.append({
            "datetime": now_str,
            "asset": asset,
            "spread": v.get("spread_percent"),
            "competitor_buy_price": (v.get("competitor_buy") or {}).get("price"),
            "competitor_sell_price": (v.get("competitor_sell") or {}).get("price"),
            "my_buy": v.get("my_suggest_buy"),
            "my_sell": v.get("my_suggest_sell"),
        })
    if len(hist) > 4000:
        hist = hist[-2000:]
    safe_write_json(HISTORICO_FILE, hist)

def append_history_snapshot(assets_out: Dict[str, Any]):
    hist = safe_read_json(HISTORICO_SNAP_FILE, [])
    if not isinstance(hist, list):
        hist = []
    hist.append({"timestamp": datetime.now().isoformat(), "data": assets_out})
    if len(hist) > 1000:
        hist = hist[-1000:]
    safe_write_json(HISTORICO_SNAP_FILE, hist)

# ---------------- Loop ----------------
def main_scanner():
    logging.info("Iniciando scanner P2P v2.5")
    cfg = load_config()

    while True:
        try:
            cfg = load_config()
            if cfg.get("paused"):
                time.sleep(max(2, int(cfg.get("scan_interval_sec", 5))))
                continue

            assets_out: Dict[str, Any] = {}
            for asset in ASSETS:
                try:
                    view = build_asset_view(asset, cfg)
                except Exception as e:
                    logging.exception(f"Error armando asset {asset}: {e}")
                    view = {
                        "competitor_buy": {"nickName": "-", "price": None},
                        "competitor_sell": {"nickName": "-", "price": None},
                        "my_suggest_buy": None,
                        "my_suggest_sell": None,
                        "spread_percent": None,
                        "sellers_table": [], "buyers_table": [],
                    }
                assets_out[asset] = view

            # ---- alertas por activo / cambios TOP ----
            state = load_state()
            thr_map = cfg.get("alert_spread_pct_by_asset") or {}
            changed = False

            for asset, v in assets_out.items():
                st_a = state.get(asset, {})
                spread = v.get("spread_percent")

                comp_sell_price = (v.get("competitor_sell") or {}).get("price")
                comp_buy_price  = (v.get("competitor_buy")  or {}).get("price")

                top_buy  = (v.get("my_suggest_buy")  is not None) and (comp_buy_price  is not None) and (v["my_suggest_buy"]  >= comp_buy_price  - 1e-9)
                top_sell = (v.get("my_suggest_sell") is not None) and (comp_sell_price is not None) and (v["my_suggest_sell"] <= comp_sell_price + 1e-9)

                thr = float(thr_map.get(asset, cfg.get("alert_spread_pct", 1.0)))
                was_alert = bool(st_a.get("alert"))
                is_alert  = (spread is not None) and (spread >= thr)
                if is_alert and not was_alert:
                    play_sound("oportunidad", cfg)

                was_top_buy  = bool(st_a.get("top_buy"))
                was_top_sell = bool(st_a.get("top_sell"))
                if top_buy and not was_top_buy:   play_sound("precio", cfg)
                if not top_buy and was_top_buy:   play_sound("vibrido", cfg)
                if top_sell and not was_top_sell: play_sound("precio", cfg)
                if not top_sell and was_top_sell: play_sound("vibrido", cfg)

                state[asset] = {"alert": is_alert, "top_buy": top_buy, "top_sell": top_sell, "last_spread": spread}
                changed = True

            if changed:
                save_state(state)

            # ---- data.json + histórico ----
            data_out = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "fiat": cfg.get("fiat", "ARS"),
                        "assets": assets_out}
            safe_write_json(DATA_FILE, data_out)
            append_history_flat(assets_out)
            append_history_snapshot(assets_out)

        except Exception as e:
            logging.exception(f"Fallo en loop principal: {e}")

        time.sleep(max(2, int(cfg.get("scan_interval_sec", 5))))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s",
                        handlers=[logging.StreamHandler()])
    main_scanner()


def pick_competitor_always(rows, side, cfg):
    return rows[0] if rows else {'price': None, 'nickName': '-'}


# === Régimen automático: detector simple de dumping vs estable ===
_REG = {"regime": "stable", "t0": 0.0}
_WIN = deque(maxlen=12)  # ~60s si el loop refresca cada 5s

def detect_regime_auto(top_buy, top_sell, now, cfg: dict) -> str:
    pos = cfg.get("positioning", {}) or {}
    win_s    = float(pos.get("window_s", 60))
    thr_drop = float(pos.get("dumping_drop_pct", 0.006))  # 0.6%
    debounce = float(pos.get("debounce_s", 45))

    if top_buy and top_sell:
        mid = (float(top_buy) + float(top_sell)) / 2.0
        _WIN.append((now, mid))

    if len(_WIN) < 6:
        return _REG["regime"]

    t0, p0 = _WIN[0]
    t1, p1 = _WIN[-1]
    if (t1 - t0) < win_s or p0 <= 0:
        return _REG["regime"]

    drop = max(0.0, (p0 - p1) / p0)
    want = "dumping" if drop >= thr_drop else "stable"

    if want != _REG["regime"] and (now - _REG.get("t0", 0)) >= debounce:
        _REG["regime"] = want
        _REG["t0"] = now
    return _REG["regime"]

