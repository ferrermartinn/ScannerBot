
# -*- coding: utf-8 -*-
"""
Dashboard P2P — v3.4.2
- Secciones: Operar / Configuraciones / Alertas / Monitoreo & registro
- Posicionamiento inteligente + Anti-persecución configurables
"""

import json, os, time
from typing import Dict, Any, List, Optional, Tuple

import streamlit as st
import altair as alt
import pandas as pd

import os, json

DATA_DIR = os.getenv("DASHBOARD_DATA_PATH", "/app/data")
DATA_FILE = os.path.join(DATA_DIR, "data.json")

# Debug rápido desde UI
def debug_box():
    st.sidebar.divider()
    dbg = st.sidebar.toggle("🔧 Debug JSON", value=False, key="dbg_json")
    if dbg:
        st.subheader("Debug: data.json leído por el dashboard")
        st.caption("Confirma que 'assets → USDT → competitor_*' tiene datos.")
        st.json(load_data())


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_asset(name: str):
    d = load_data()
    return d["assets"].get(name, {})


DATA_FILE   = os.path.join(DATA_DIR, "data.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
HIST_FILE   = os.path.join(DATA_DIR, "historico_spreads.json")


ASSETS = ["USDT", "BTC", "ETH", "XRP"]

DEFAULT_CFG = {
    "verified_only": False,
    "paused": False,
    "mute_alerts": False,
    "fiat": "ARS",
    "scan_interval_sec": 5,
    "refresh_sec": 8,
    "margins": {"USDT": 0.01, "BTC": 0.01, "ETH": 0.01, "XRP": 0.01},
    "alert_spread_pct": 1.0,
    "alert_spread_pct_by_asset": {},
    "alert_min_ars": 1500.0,
    "alert_min_ars_by_asset": {},
    "pozo_ref_usd": 900.0,
    "min_order_pct": 0.10,
    "top_compete_n": 5,
    "size_widen_pct": 25.0,
    "price_delta_abs": 0.01,
    "price_delta_pct": 0.1,
    "min_net_spread_pct": 0.3,
    "positioning": {
        "enable": True,
        "small_pozo_threshold_usd": 700.0,
        "small_range": [3, 6],
        "large_range": [1, 3],
        "regime_mode": "auto",
        "dumping_window_n": 24,
        "dumping_drop_pct": 0.5
    },
    "reprice_guard": {
        "enable": True,
        "min_stick_cycles": 3,
        "min_step_abs": 0.00,
        "min_step_pct": 0.00
    },
    "vol_sounds": {
        "alerta_caida": 0.5,
        "alerta_precio": 0.4,
        "alerta_rentable": 0.9,
        "alerta_vibrido": 0.2,
    },
    "pinned_asset": None,
    "pay_types": [],
    # >>> NUEVO <<<
    "competitor_filters": {
        "pozo_usd_min": 500.0,
        "pozo_usd_max": 1300.0,
        "min_order_ars": 100000.0
    },
}

def deepmerge(base: dict, defaults: dict) -> dict:
    out = dict(defaults)
    base = base or {}
    for k, v in base.items():
        if isinstance(v, dict) and isinstance(defaults.get(k), dict):
            out[k] = deepmerge(v, defaults.get(k))
        else:
            out[k] = v
    return out

def read_json(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path: str, payload):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        pass

def load_config() -> dict:
    return deepmerge(read_json(CONFIG_FILE, {}) or {}, DEFAULT_CFG)

def save_config(cfg: dict):
    write_json(CONFIG_FILE, cfg)


def as_float(x) -> Optional[float]:
    try:
        if isinstance(x, str) and x.endswith("%"):
            x = x[:-1]
        return float(x)
    except Exception:
        return None

def fmt_price(x) -> str:
    try:
        v = float(x)
        return f"{v:,.2f}".replace(",", ".")
    except Exception:
        return "-"

def top_flags(info: dict) -> Tuple[bool, bool]:
    my_buy  = info.get("my_suggest_buy")
    my_sell = info.get("my_suggest_sell")
    comp_sell = (info.get("competitor_sell") or {}).get("price")
    comp_buy  = (info.get("competitor_buy")  or {}).get("price")
    try:
        top_buy  = (my_buy is not None) and (comp_buy  is not None) and (float(my_buy)  >= float(comp_buy)  - 1e-9)
        top_sell = (my_sell is not None) and (comp_sell is not None) and (float(my_sell) <= float(comp_sell) + 1e-9)
    except Exception:
        top_buy, top_sell = False, False
    return top_buy, top_sell

def fx_usdt_from_assets(assets: Dict[str, Any]) -> float:
    usdt = (assets or {}).get("USDT") or {}
    p1 = as_float((usdt.get("competitor_buy")  or {}).get("price"))
    p2 = as_float((usdt.get("competitor_sell") or {}).get("price"))
    vals = [p for p in (p1, p2) if p]
    if vals: return sum(vals)/len(vals)
    try:
        stbl = usdt.get("sellers_table") or []
        btbl = usdt.get("buyers_table") or []
        c = []
        if stbl: c.append(as_float(stbl[0].get("price")))
        if btbl: c.append(as_float(btbl[0].get("price")))
        c = [x for x in c if x]
        return sum(c)/len(c) if c else 1.0
    except Exception:
        return 1.0

def _cap_ars_from_cfg(cfg: dict, assets: dict) -> float:
    fx = fx_usdt_from_assets(assets or {})
    pozo = float(cfg.get("pozo_ref_usd", 400.0))
    return pozo * float(fx or 1.0)

def _apply_comp_filters(rows: list, cfg: dict, assets: dict) -> list:
    cf = (cfg or {}).get("competitor_filters") or {}
    pozo_min = float(cf.get("pozo_usd_min", 0.0))
    pozo_max = float(cf.get("pozo_usd_max", 10**9))
    min_order_ars = float(cf.get("min_order_ars", 0.0))

    fx = fx_usdt_from_assets(assets or {})
    pozo_min_ars = pozo_min * fx
    pozo_max_ars = pozo_max * fx
    cap_ars = _cap_ars_from_cfg(cfg, assets)

    out = []
    for r in rows or []:
        try:
            minAmt = as_float(r.get("minAmount"))
            totAmt = as_float(r.get("totalAmount"))
            if minAmt is None or totAmt is None:
                continue
            if minAmt < min_order_ars:
                continue
            if not (pozo_min_ars <= totAmt <= pozo_max_ars):
                continue
            if minAmt > cap_ars:
                continue
            out.append(r)
        except Exception:
            continue
    return out


def badge_html(text: str, color: str) -> str:
    return f"<span style='background:{color};color:#000;padding:2px 8px;border-radius:10px;font-weight:700;font-size:0.7rem;'>{text}</span>"

def spread_badge(spread):
    if spread is None:
        st.markdown("<div style='text-align:right;color:#999;'>Spread —</div>", unsafe_allow_html=True)
        return
    col = "#3c78d8" if float(spread) >= 0 else "#cc0000"
    st.markdown(
        f"<div style='text-align:right;font-weight:700;color:{col}'>Spread {float(spread):.2f}%</div>",
        unsafe_allow_html=True
    )

def header_asset(title: str, spread):
    cols = st.columns([6,1])
    with cols[0]:
        st.markdown(f"## {title}")
    with cols[1]:
        spread_badge(spread)

def block_buy_html(info: dict) -> str:
    b = info.get("competitor_buy") or {}
    bname = b.get("nickName", "-")
    bprice = fmt_price(b.get("price"))
    my_buy = fmt_price(info.get("my_suggest_buy"))
    top_buy, _ = top_flags(info)
    top_badge = badge_html('TOP Compra', '#b6d7a8') if top_buy else ""
    return f"""
      <div style="margin-bottom:4px;">{top_badge}</div>
      <div>
        <span style="color:#93c47d; font-weight:700;">Competidor (Compra)</span>:
        <span style="font-weight:700;">{bname}</span> @ <span style="font-weight:700;">{bprice}</span>
        <span style="opacity:0.6; padding:0 6px;">→</span>
        <span style="color:#93c47d; font-weight:800;">Mi Compra (aviso)</span>:
        <span style="font-size:1.1rem; font-weight:800;">{my_buy}</span>
      </div>
    """

def block_sell_html(info: dict) -> str:
    s = info.get("competitor_sell") or {}
    sname = s.get("nickName", "-")
    sprice = fmt_price(s.get("price"))
    my_sell = fmt_price(info.get("my_suggest_sell"))
    _, top_sell = top_flags(info)
    top_badge = badge_html('TOP Venta', '#f4cccc') if top_sell else ""
    return f"""
      <div style="margin-bottom:8px;">{top_badge}</div>
      <div>
        <span style="color:#e06666; font-weight:700;">Competidor (Venta)</span>:
        <span style="font-weight:700;">{sname}</span> @ <span style="font-weight:700;">{sprice}</span>
        <span style="opacity:0.6; padding:0 6px;">→</span>
        <span style="color:#e06666; font-weight:800;">Mi Venta (aviso)</span>:
        <span style="font-size:1.1rem; font-weight:800;">{my_sell}</span>
      </div>
    """

def render_blocks(info: dict):
    tb, ts = top_flags(info)
    buy_html  = block_buy_html(info)
    sell_html = block_sell_html(info)
    if tb and ts:
        st.markdown(
            f"""
            <div style="background:rgba(40,150,40,0.10);
                        border:1px solid rgba(40,150,40,0.25);
                        padding:12px 14px; border-radius:12px;">
              <div style="font-weight:700;margin-bottom:6px;color:#b6d7a8;">✅ Bien posicionado</div>
              <div style="font-size:0.95rem; line-height:1.8">{buy_html}</div>
              <div style="height:6px"></div>
              <div style="font-size:0.95rem; line-height:1.8">{sell_html}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(f"<div style='font-size:0.95rem; line-height:1.8'>{buy_html}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.95rem; line-height:1.8'>{sell_html}</div>", unsafe_allow_html=True)

def button_pin(asset: str):
    pinned = st.session_state.get("pinned_asset")
    if pinned == asset:
        if st.button("Quitar 📌", key=f"unpin_{asset}", use_container_width=True):
            c = load_config(); c["pinned_asset"] = None; save_config(c)
            st.session_state["pinned_asset"] = None
            st.session_state["ui_select_pin"] = "Ninguno"
    else:
        if st.button("Fijar 📌", key=f"pin_{asset}", use_container_width=True):
            c = load_config(); c["pinned_asset"] = asset; save_config(c)
            st.session_state["pinned_asset"] = asset
            st.session_state["ui_select_pin"] = asset

def _sizing_panel(asset: str, info: dict):
    cfg = load_config()
    data = load_data()
    fx = fx_usdt_from_assets(data.get("assets") or {})
    pozo = float(cfg.get("pozo_ref_usd", 400.0))
    cap_ars = pozo * float(fx or 1.0)
    sp  = as_float(info.get("spread_pct") or info.get("spread_percent"))
    pnl = cap_ars * (sp/100.0) if sp is not None else None
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Pozo (USD)", f"{pozo:,.0f}")
    with c2: st.metric("ARS/USDT (est.)", fmt_price(fx))
    with c3: st.metric("P&L estimado (ARS)", "-" if pnl is None else f"{pnl:,.0f}")

# --- Status de data.json en sidebar ---
import os, json, time, streamlit as st

def _file_health(path="/app/data/data.json"):
    try:
        stt = os.stat(path)
        d = json.load(open(path, "r", encoding="utf-8"))
        u = (d.get("assets") or {}).get("USDT", {}) or {}
        return {
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stt.st_mtime)),
            "size": stt.st_size,
            "buyers": len(u.get("buyers_table") or []),
            "sellers": len(u.get("sellers_table") or []),
        }
    except Exception as e:
        return {"error": str(e)}

with st.sidebar:
    st.subheader("Data status")
    h = _file_health()
    if "error" in h:
        st.error(h["error"])
    else:
        st.metric("Updated", h["updated_at"])
        st.metric("Size (bytes)", h["size"])
        st.metric("Buyers/Sellers", f"{h['buyers']}/{h['sellers']}")
# --- fin status ---


def _depth_panel(info: dict, depth: int = 6):
    cfg = load_config()
    assets_all = (load_data() or {}).get("assets") or {}

    sellers_raw = (info.get("sellers_table") or [])
    buyers_raw  = (info.get("buyers_table")  or [])

    sellers = _apply_comp_filters(sellers_raw, cfg, assets_all)[:depth]
    buyers  = _apply_comp_filters(buyers_raw,  cfg, assets_all)[:depth]

    c1, c2 = st.columns(2)
    with c1:
        st.caption("Vendedores comparables (mejores primero)")
        for r in sellers:
            st.markdown(f"- **{r.get('nickName','-')}** @ {fmt_price(r.get('price'))} · min {fmt_price(r.get('minAmount'))} · total {fmt_price(r.get('totalAmount'))}")
    with c2:
        st.caption("Compradores comparables (mejores primero)")
        for r in buyers:
            st.markdown(f"- **{r.get('nickName','-')}** @ {fmt_price(r.get('price'))} · min {fmt_price(r.get('minAmount'))} · total {fmt_price(r.get('totalAmount'))}")

def card_compact(asset: str, info: dict):
    with st.container(border=True):
        spread = info.get("spread_pct") or info.get("spread_percent")
        header_asset(asset, spread)
        render_blocks(info)
        c = st.columns([1,2,3])
        with c[0]:
            button_pin(asset)
        with st.expander("📊 Sizing & PnL"):
            _sizing_panel(asset, info)
        with st.expander("📚 Profundidad del libro (Top)"):
            _depth_panel(info)

def card_expanded(asset: str, info: dict):
    with st.container(border=True):
        spread = info.get("spread_pct") or info.get("spread_percent")
        header_asset(asset, spread)
        render_blocks(info)
        row = st.columns([1,3,3,3])
        with row[0]:
            button_pin(asset)
        st.divider()
        st.markdown("**Alrededor de mi COMPRA (vs vendedores)**")
        st.caption("Usa la profundidad (Top) para ver más detalle.")
        with st.expander("Ver lista de vendedores (Top)"):
            _depth_panel(info, depth=6)
        with st.expander("📊 Sizing & PnL"):
            _sizing_panel(asset, info)

def load_history_last_minutes(minutes: int = 30) -> pd.DataFrame:
    raw = read_json(HIST_FILE, []) or []
    if not raw:
        return pd.DataFrame(columns=["datetime","asset","spread"])
    df = pd.DataFrame(raw)
    if "datetime" not in df.columns:
        return pd.DataFrame(columns=["datetime","asset","spread"])
    try:
        df["datetime"] = pd.to_datetime(df["datetime"])
    except Exception:
        return pd.DataFrame(columns=["datetime","asset","spread"])
    tmin = pd.Timestamp.utcnow() - pd.Timedelta(minutes=minutes)
    df = df[df["datetime"] >= tmin.tz_localize(None)]
    return df.sort_values("datetime")

def render_history(seconds_window: int = 1800):
    st.subheader("🕒 Spreads últimos 30 minutos")
    df = load_history_last_minutes(minutes=seconds_window//60)
    if df.empty:
        st.info("Sin datos suficientes aún."); return
    df["spread"] = pd.to_numeric(df["spread"], errors="coerce")
    df = df.dropna(subset=["spread"])
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X("datetime:T", title="Tiempo"),
        y=alt.Y("spread:Q", title="Spread %"),
        color=alt.Color("asset:N", title="Activo")
    ).properties(height=260)
    st.altair_chart(chart, use_container_width=True)

def sidebar_sections(cfg: dict) -> str:
    st.sidebar.header("Panel")
    section = st.sidebar.radio("Sección", ["Operar", "Configuraciones", "Alertas", "Monitoreo & registro"], index=0, key="sec_radio")
    st.session_state["ui_section"] = section

    if section == "Operar":
        if "ui_verified_only" not in st.session_state:
            st.session_state["ui_verified_only"] = bool(cfg.get("verified_only", False))
        def _on_change_verified():
            c = load_config(); c["verified_only"] = bool(st.session_state.get("ui_verified_only")); save_config(c)
        st.sidebar.toggle("Solo comerciantes verificados", key="ui_verified_only", on_change=_on_change_verified)

        c1, c2 = st.sidebar.columns(2)
        with c1:
            if st.button("⏸️ Pausar", use_container_width=True, key="pause_btn"):
                c = load_config(); c["paused"] = True; save_config(c)
        with c2:
            if st.button("▶️ Reanudar", use_container_width=True, key="resume_btn"):
                c = load_config(); c["paused"] = False; save_config(c)

        if st.sidebar.button("🔇 Mute" if not cfg.get("mute_alerts") else "🔊 Unmute", use_container_width=True, key="mute_btn"):
            c = load_config(); c["mute_alerts"] = not bool(c.get("mute_alerts")); save_config(c)

        st.sidebar.divider()
        st.sidebar.subheader("📌 Activo anclado")
        if "ui_select_pin" not in st.session_state:
            st.session_state["ui_select_pin"] = cfg.get("pinned_asset") or "Ninguno"

        def _on_change_pin():
            val = st.session_state.get("ui_select_pin", "Ninguno")
            new_pin = None if val == "Ninguno" else val
            c = load_config(); c["pinned_asset"] = new_pin; save_config(c)
            st.session_state["pinned_asset"] = new_pin

        st.sidebar.selectbox(
            "Elegí si querés anclar un activo",
            options=["Ninguno"] + ASSETS,
            index=(["Ninguno"] + ASSETS).index(st.session_state["ui_select_pin"]),
            key="ui_select_pin",
            on_change=_on_change_pin,
        )
        st.sidebar.toggle("Compactar no anclados", key="compact_others", value=st.session_state.get("compact_others", True))
        st.sidebar.toggle("Ocultar no anclados", key="hide_others", value=st.session_state.get("hide_others", False))

        st.sidebar.divider()
        st.sidebar.subheader("🔁 Auto-actualización")
        st.sidebar.toggle("Activar", key="auto_update", value=st.session_state.get("auto_update", True))
        st.sidebar.number_input("Frecuencia (seg)", min_value=2, max_value=60, step=1, key="refresh_sec", value=int(cfg.get("refresh_sec", 8)))

    if section == "Configuraciones":
        st.sidebar.subheader("💰 Pozo y tamaños")
        pozo = st.sidebar.number_input("Pozo ref (USD)", min_value=0.0, value=float(cfg.get("pozo_ref_usd", 400.0)), step=50.0, format="%.2f", key="pozo_ref_usd")
        min_pct = st.sidebar.slider("Mínimo por orden (% del pozo)", 1.0, 50.0, float(cfg.get("min_order_pct", 0.10)*100.0), 1.0, key="min_order_pct") / 100.0
        topn   = st.sidebar.slider("Máximo Top para anclar", 1, 10, int(cfg.get("top_compete_n", 5)), 1, key="top_compete_n")
        widen  = st.sidebar.slider("Cercanía de competidores ±%", 5.0, 50.0, float(cfg.get("size_widen_pct", 25.0)), 1.0, key="size_widen_pct")

        st.sidebar.subheader("⚙️ Reglas de ajuste de precio")
        delta_abs = st.sidebar.number_input("Delta absoluto (ARS)", min_value=0.00, value=float(cfg.get("price_delta_abs", 0.01)), step=0.01, format="%.2f", key="delta_abs")
        delta_pct = st.sidebar.number_input("Delta porcentual (%)", min_value=0.0, value=float(cfg.get("price_delta_pct", 0.1)), step=0.05, format="%.2f", key="delta_pct")
        min_net   = st.sidebar.number_input("No ajustar si spread neto < (%)", min_value=0.0, value=float(cfg.get("min_net_spread_pct", 0.3)), step=0.05, format="%.2f", key="min_net")
        st.sidebar.caption("Regla: competidor directo, verificado y Top-7 ⇒ max(Δ abs, Precio×Δ%).")

        st.sidebar.subheader("🎯 Posicionamiento inteligente")
        pos = cfg.get("positioning") or {}
        pos_enable = st.sidebar.toggle("Activar", key="pos_enable_toggle", value=bool(pos.get("enable", True)))
        small_thr  = st.sidebar.number_input("Umbral pozo pequeño (USD)", min_value=0.0, value=float(pos.get("small_pozo_threshold_usd", 700.0)), step=50.0, format="%.2f", key="small_thr")
        c1, c2 = st.sidebar.columns(2)
        with c1:
            s_min = st.number_input("Pequeño rango min", min_value=1, max_value=10, value=int((pos.get("small_range") or [3,6])[0]), step=1, key="s_min")
        with c2:
            s_max = st.number_input("Pequeño rango max", min_value=1, max_value=10, value=int((pos.get("small_range") or [3,6])[1]), step=1, key="s_max")
        c3, c4 = st.sidebar.columns(2)
        with c3:
            l_min = st.number_input("Grande rango min", min_value=1, max_value=10, value=int((pos.get("large_range") or [1,3])[0]), step=1, key="l_min")
        with c4:
            l_max = st.number_input("Grande rango max", min_value=1, max_value=10, value=int((pos.get("large_range") or [1,3])[1]), step=1, key="l_max")
        regime_mode = st.sidebar.selectbox("Régimen", ["auto","stable","dumping"], index=["auto","stable","dumping"].index(str(pos.get("regime_mode","auto")).lower()), key="regime_mode")
        c5, c6 = st.sidebar.columns(2)
        with c5:
            dump_win = st.number_input("Ventana dumping (snapshots)", min_value=5, max_value=200, value=int(pos.get("dumping_window_n", 24)), step=1, key="dump_win")
        with c6:
            dump_drop = st.number_input("Umbral caída dumping (%)", min_value=0.0, max_value=10.0, value=float(pos.get("dumping_drop_pct", 0.5)), step=0.1, format="%.1f", key="dump_drop")

        st.sidebar.subheader("🛡️ Anti-persecución")
        guard = cfg.get("reprice_guard") or {}
        guard_en = st.sidebar.toggle("Activar", key="guard_enable_toggle", value=bool(guard.get("enable", True)))
        stick_min = st.sidebar.slider("Permanencia mínima (ciclos)", 1, 10, int(guard.get("min_stick_cycles", 3)), 1, key="stick_min")
        g1, g2 = st.sidebar.columns(2)
        with g1:
            step_abs = st.number_input("Cambio mínimo abs (ARS)", min_value=0.00, value=float(guard.get("min_step_abs", 0.00)), step=0.01, format="%.2f", key="step_abs")
        with g2:
            step_pct = st.number_input("Cambio mínimo %", min_value=0.0, value=float(guard.get("min_step_pct", 0.00)), step=0.05, format="%.2f", key="step_pct")

        st.sidebar.subheader("⏱️ Frecuencias")
        scan_iv = st.sidebar.number_input("Intervalo del scanner (seg)", min_value=2, max_value=60, step=1, value=int(cfg.get("scan_interval_sec", 5)), key="scan_iv")
        refresh = st.sidebar.number_input("Refresh del panel (seg)", min_value=2, max_value=60, step=1, value=int(cfg.get("refresh_sec", 8)), key="refresh_panel")

        st.sidebar.subheader("🧮 Márgenes por activo (ARS)")
        new_marg = {}
        cols = st.sidebar.columns(2)
        for i, a in enumerate(ASSETS):
            with cols[i % 2]:
                new_marg[a] = st.number_input(f"{a}", min_value=0.00, value=float((cfg.get("margins") or {}).get(a, 0.01)), step=0.01, format="%.2f", key=f"m_{a}")

        st.sidebar.subheader("💳 Métodos de pago (filtro)")
        ALL_PAY = ["MERCADOPAGO", "LEMON_CASH_APP", "BRUBANK", "NARANJAX"]
        sel_pay = st.sidebar.multiselect("Filtrar por métodos", ALL_PAY, default=cfg.get("pay_types", []), key="pay_types_sel")

        if st.sidebar.button("💾 Guardar configuraciones", use_container_width=True, key="save_cfg"):
            c = load_config()
            c["pozo_ref_usd"]   = float(pozo)
            c["min_order_pct"]  = float(min_pct)
            c["top_compete_n"]  = int(topn)
            c["size_widen_pct"] = float(widen)
            c["scan_interval_sec"] = int(scan_iv)
            c["refresh_sec"]    = int(refresh)
            c["margins"]        = {a: float(new_marg[a]) for a in ASSETS}
            c["pay_types"]      = sel_pay
            c["price_delta_abs"]   = float(delta_abs)
            c["price_delta_pct"]   = float(delta_pct)
            c["min_net_spread_pct"]= float(min_net)
            c["positioning"] = {
                "enable": bool(pos_enable),
                "small_pozo_threshold_usd": float(small_thr),
                "small_range": [int(s_min), int(s_max)],
                "large_range": [int(l_min), int(l_max)],
                "regime_mode": regime_mode,
                "dumping_window_n": int(dump_win),
                "dumping_drop_pct": float(dump_drop),
            }
            c["reprice_guard"] = {
                "enable": bool(guard_en),
                "min_stick_cycles": int(stick_min),
                "min_step_abs": float(step_abs),
                "min_step_pct": float(step_pct),
            }
            save_config(c)
            st.success("Configuraciones guardadas")

    if section == "Alertas":
        st.sidebar.subheader("🔕 Sonido")
        if st.sidebar.button("🔇 Mute" if not cfg.get("mute_alerts") else "🔊 Unmute", use_container_width=True, key="mute_btn_alertas"):
            c = load_config(); c["mute_alerts"] = not bool(c.get("mute_alerts")); save_config(c)

        st.sidebar.subheader("🎯 Umbrales")
        thr_global = st.sidebar.number_input("Spread % global", min_value=0.0, value=float(cfg.get("alert_spread_pct", 1.0)), step=0.1, format="%.2f", key="thr_global")
        min_ars_global = st.sidebar.number_input("PnL mínimo (ARS)", min_value=0.0, value=float(cfg.get("alert_min_ars", 1500.0)), step=100.0, format="%.2f", key="min_ars_global")
        with st.sidebar.expander("Por activo"):
            thr_by, min_by = {}, {}
            for a in ASSETS:
                col1, col2 = st.columns(2)
                with col1:
                    thr_by[a] = st.number_input(f"{a} %", min_value=0.0,
                                                value=float((cfg.get("alert_spread_pct_by_asset") or {}).get(a, thr_global)),
                                                step=0.1, format="%.2f", key=f"thr_{a}")
                with col2:
                    min_by[a] = st.number_input(f"{a} ARS", min_value=0.0,
                                                value=float((cfg.get("alert_min_ars_by_asset") or {}).get(a, min_ars_global)),
                                                step=100.0, format="%.2f", key=f"min_{a}")
        if st.sidebar.button("💾 Guardar umbrales", use_container_width=True, key="save_alerts"):
            c = load_config()
            c["alert_spread_pct"] = float(thr_global)
            c["alert_min_ars"] = float(min_ars_global)
            c["alert_spread_pct_by_asset"] = {a: float(thr_by[a]) for a in ASSETS}
            c["alert_min_ars_by_asset"]     = {a: float(min_by[a]) for a in ASSETS}
            save_config(c); st.success("Umbrales guardados")

        st.sidebar.subheader("🔊 Volúmenes")
        vols = cfg.get("vol_sounds") or {}
        v_vibr = st.sidebar.slider("Vibrido", 0.0, 1.0, float(vols.get("alerta_vibrido", 0.2)), 0.01, key="vol_vibr")
        v_prec = st.sidebar.slider("Precio (TOP)", 0.0, 1.0, float(vols.get("alerta_precio", 0.4)), 0.01, key="vol_prec")
        v_caida = st.sidebar.slider("Caída", 0.0, 1.0, float(vols.get("alerta_caida", 0.5)), 0.01, key="vol_caida")
        v_rent = st.sidebar.slider("Oportunidad fuerte", 0.0, 1.0, float(vols.get("alerta_rentable", 0.9)), 0.01, key="vol_rent")
        if st.sidebar.button("💾 Guardar audio", use_container_width=True, key="save_audio"):
            c = load_config()
            c["vol_sounds"] = {
                "alerta_vibrido": float(v_vibr),
                "alerta_precio":  float(v_prec),
                "alerta_caida":   float(v_caida),
                "alerta_rentable":float(v_rent),
            }
            save_config(c); st.success("Volúmenes guardados")

    if section == "Monitoreo & registro":
        if st.sidebar.button("🧹 Limpiar histórico (spreads)", use_container_width=True, key="clear_hist"):
            write_json(HIST_FILE, []); st.success("Histórico limpiado")
        if st.sidebar.button("📄 Generar reporte", use_container_width=True, key="gen_report"):
            st.session_state["generate_report_now"] = True
            st.success("Reporte generado (panel central)")
    return section

def _generate_report():
    data = load_data()
    assets = data.get("assets") or {}
    fx = fx_usdt_from_assets(assets)
    cfg = load_config()
    pozo = float(cfg.get("pozo_ref_usd", 400.0))
    cap_ars = pozo * float(fx or 1.0)

    rows = []
    for a in ASSETS:
        v = assets.get(a) or {}
        sp  = as_float(v.get("spread_pct") or v.get("spread_percent"))
        pnl = cap_ars * (sp/100.0) if sp is not None else None
        rows.append({
            "Activo": a,
            "Spread %": sp,
            "Mi compra (aviso)": v.get("my_suggest_buy"),
            "Mi venta (aviso)": v.get("my_suggest_sell"),
            "P&L est. (ARS)": pnl
        })
    df = pd.DataFrame(rows)
    st.subheader("📄 Reporte actual")
    st.dataframe(df.style.format({
        "Spread %": "{:.2f}",
        "Mi compra (aviso)": "{:,.2f}",
        "Mi venta (aviso)": "{:,.2f}",
        "P&L est. (ARS)": "{:,.0f}"
    }), use_container_width=True)

st.set_page_config(layout="wide", page_title="Dashboard P2P")

cfg = load_config()
section = sidebar_sections(cfg)
debug_box()  # ← muestra el JSON si activás el toggle


data = load_data()
assets = data.get("assets") or {}
ts = data.get("timestamp","-")

if section == "Operar":
    st.markdown(f"# Dashboard P2P — <span style='color:#999'>actualizado {ts}</span>", unsafe_allow_html=True)

    pinned = st.session_state.get("pinned_asset")
    hide_others = st.session_state.get("hide_others", False)
    compact_others = st.session_state.get("compact_others", True)

    if pinned and pinned in ASSETS and assets.get(pinned):
        card_expanded(pinned, assets[pinned])

    others = [a for a in ASSETS if a != pinned]
    if not pinned:
        cols = st.columns(2)
        for i, a in enumerate(ASSETS):
            with cols[i % 2]:
                card_compact(a, assets.get(a) or {})
    else:
        if not hide_others:
            st.markdown("#### Otros activos")
            cols = st.columns(3 if compact_others else 2)
            for i, a in enumerate(others):
                with cols[i % (3 if compact_others else 2)]:
                    card_compact(a, assets.get(a) or {})

    st.divider()
    render_history(seconds_window=1800)

    if st.session_state.get("auto_update", True):
        try:
            time.sleep(max(2, int(st.session_state.get("refresh_sec", int(cfg.get("refresh_sec", 8))))))
        except Exception:
            time.sleep(8)
        st.rerun()

elif section == "Configuraciones":
    st.markdown("# Configuraciones")
    st.info("Ajustá parámetros del scanner y del panel desde la izquierda.")

elif section == "Alertas":
    st.markdown("# Alertas")
    st.info("Umbrales y volúmenes de audio editables desde la izquierda.")

elif section == "Monitoreo & registro":
    st.markdown("# Monitoreo & registro")
    if st.session_state.get("generate_report_now"):
        _generate_report()
        st.session_state["generate_report_now"] = False
    st.divider()
    st.subheader("🕒 Spreads (histórico)")
    render_history(seconds_window=1800)
