from pathlib import Path
import json, tempfile, os

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

INJECT = r"""
# === injected: pay types controls ===
from pathlib import Path
import json, tempfile, os, streamlit as st

_CFG_PATH = Path("/app/data/config.json")

def _cfg_load_sidebar():
    # fallback sensato si no existe
    try:
        cfg = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            raise ValueError("cfg no dict")
    except Exception:
        cfg = {"fiat":"ARS","assets":["USDT","BTC","ETH","XRP"],"pay_types":[],"tick":0.01,"buy_undercut":True,"sell_overcut":True}
    return cfg

def _cfg_save_sidebar(cfg: dict):
    # guardado atómico
    tmp = _CFG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _CFG_PATH)

def sidebar_paytypes_controls():
    cfg = _cfg_load_sidebar()
    pay_types = cfg.get("pay_types") or []
    st.sidebar.markdown("### Filtro de pagos")
    st.sidebar.caption(f"Actual: {', '.join(pay_types) if pay_types else 'sin filtro'}")

    # opciones rápidas (puedes ampliar)
    preset = st.sidebar.checkbox("Mercado Pago", value=("mercado pago" in [p.lower() for p in pay_types]))
    custom = st.sidebar.text_input("Extras separados por coma", value=",".join([p for p in pay_types if p.lower() not in ('mercado pago','mercadopago','mp')]))

    colA, colB = st.sidebar.columns(2)
    save = colA.button("Guardar", use_container_width=True)
    clear = colB.button("Quitar filtro", use_container_width=True)

    if clear:
        cfg["pay_types"] = []
        _cfg_save_sidebar(cfg)
        st.sidebar.success("Filtro eliminado")
        st.rerun()

    if save:
        chosen = []
        if preset:
            # añadimos todas las variantes útiles de Mercado Pago
            chosen.extend(["mercado pago","mercadopago","mp"])
        extra = [x.strip() for x in custom.split(",") if x.strip()]
        # dedupe manteniendo orden
        seen = set(); result=[]
        for x in chosen+extra:
            xl = x.lower()
            if xl not in seen:
                seen.add(xl); result.append(x)
        cfg["pay_types"] = result
        _cfg_save_sidebar(cfg)
        st.sidebar.success("Filtro guardado")
        st.rerun()
"""

# 1) inyectar helpers si faltan
if "def sidebar_paytypes_controls()" not in s:
    # insertar tras imports
    lines = s.splitlines()
    last_imp = 0
    for i, ln in enumerate(lines):
        t = ln.strip()
        if t.startswith("import ") or t.startswith("from "):
            last_imp = i
        elif last_imp and t and not t.startswith("#"):
            break
    lines.insert(last_imp+1, INJECT.strip())
    s = "\n".join(lines)

# 2) invocar el control en el sidebar (una sola vez)
if "sidebar_paytypes_controls()" not in s:
    # buscamos algún patrón estable del sidebar; si no, lo añadimos al final del bloque principal
    hook = "st.sidebar"
    if hook in s:
        s = s.replace(hook, "sidebar_paytypes_controls()\n" + hook, 1)
    else:
        s += "\n\n# call sidebar pay types controls\sidebar_paytypes_controls()\n"

P.write_text(s, encoding="utf-8")
print("OK: dashboard ahora permite alternar pay_types desde el sidebar")