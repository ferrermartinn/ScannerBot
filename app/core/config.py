# -*- coding: utf-8 -*-
"""
config.py — utilidades para leer/escribir config.json con defaults.
Uso:
    from config import load_config, save_config, get_volume, is_muted
"""

import json, os
from typing import Any, Dict

CONFIG_FILE = "config.json"

DEFAULTS: Dict[str, Any] = {
    "paused": False,
    "mute_alerts": False,
    "pozo_ref_usd": 400.0,
    "refresh_sec": 8,
    "live_update": True,
    "alert_spread_pct": 1.0,
    "alert_spread_pct_by_asset": {},
    "alert_min_ars": 1500.0,
    "alert_min_ars_by_asset": {},
    "min_liquidity_fiat": 0.0,
    "compact_mode": False,
    "large_ui": False,
    "blacklist": [],
    "ui_toasts": True,
    "pause_on_pin": False,
    "margins": {"USDT": 0.01, "BTC": 10.0, "ETH": 1.0, "XRP": 0.01},
    "margin_steps": {"USDT": 0.01, "BTC": 10.0, "ETH": 1.0, "XRP": 0.01},
    "scan_interval_sec": 5,
    "theme": "Midnight",
    "vol_sounds": {
        "alerta_caida": 0.5,
        "alerta_precio": 0.4,
        "alerta_rentable": 0.9,
        "alerta_vibrido": 0.2
    },
    # opcional
    "focused_asset": None
}

def _deepmerge(base: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base) if isinstance(base, dict) else {}
    for k, v in defaults.items():
        if isinstance(v, dict):
            out[k] = _deepmerge(out.get(k, {}) if isinstance(out.get(k, {}), dict) else {}, v)
        else:
            out.setdefault(k, v)
    return out

def load_config() -> Dict[str, Any]:
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    cfg = _deepmerge(cfg, DEFAULTS)
    save_config(cfg)  # asegura que el archivo exista y complete claves faltantes
    return cfg

def save_config(cfg: Dict[str, Any]) -> None:
    try:
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CONFIG_FILE)
    except Exception:
        pass

def is_muted(cfg: Dict[str, Any] = None) -> bool:
    if cfg is None: cfg = load_config()
    return bool(cfg.get("mute_alerts", False))

def get_volume(name: str, default: float = 0.3, cfg: Dict[str, Any] = None) -> float:
    if cfg is None: cfg = load_config()
    vol_map = cfg.get("vol_sounds") or {}
    try:
        return float(vol_map.get(name, default))
    except Exception:
        return default

def get_refresh_sec(cfg: Dict[str, Any] = None) -> int:
    if cfg is None: cfg = load_config()
    try:
        return int(cfg.get("refresh_sec", 8))
    except Exception:
        return 8

def set_focused_asset(asset: str = None) -> None:
    cfg = load_config()
    cfg["focused_asset"] = asset
    save_config(cfg)

def get_focused_asset(cfg: Dict[str, Any] = None):
    if cfg is None: cfg = load_config()
    return cfg.get("focused_asset", None)
