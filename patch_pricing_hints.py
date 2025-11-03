from pathlib import Path
import re, py_compile

P = Path("/app/app/service/scanner_p2p.py")
s = P.read_text(encoding="utf-8")

INJECT = r"""
# === injected: pricing hints ===
def _round2(x):
    try:
        return float(f"{float(x):.2f}")
    except Exception:
        return None

def compute_my_hints(top_buy, top_sell, tick_buy=0.01, tick_sell=0.01):
    """
    Regla maker:
      - Mi Compra (aviso) = top_buy + tick_buy  (pagás apenas más para atraer vendedores)
      - Mi Venta  (aviso) = top_sell - tick_sell (cobrás apenas menos para atraer compradores)
    """
    b = _round2((top_buy or 0) + (tick_buy or 0))
    s = _round2((top_sell or 0) - (tick_sell or 0))
    return b, s
"""

# 1) inyectar helpers tras los imports si no existen
if "def compute_my_hints(" not in s:
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

# 2) dentro de build_asset_view(...) asegurar que usa compute_my_hints
# buscamos la construcción del dict 'meta' y agregamos my_buy_hint / my_sell_hint correctos
# patrón: meta = {...} o d['meta']={...}
s = re.sub(
    r"(meta\s*=\s*\{[\s\S]*?\})",
    r"\1",
    s,
    flags=re.M
)

# reemplazar cualquier asignación previa de mis hints por la nueva regla
s = re.sub(
    r"(my_buy_hint\s*=\s*.*\n|my_sell_hint\s*=\s*.*\n)",
    r"",
    s
)

# insertar o reasignar inmediatamente después de obtener top_buy/top_sell
s = re.sub(
    r"(?P<lead>top_buy\s*=\s*.*\n\s*top_sell\s*=\s*.*\n)",
    r"\g<lead>    my_buy_hint, my_sell_hint = compute_my_hints(top_buy, top_sell, cfg.get('tick_buy',0.01), cfg.get('tick_sell',0.01))\n",
    s
)

# asegurar que los hints aparecen en el dict `meta`
if "my_buy_hint" not in s or "my_sell_hint" not in s:
    s = re.sub(
        r"(meta\s*=\s*\{)",
        r"\1\n        'my_buy_hint': my_buy_hint,\n        'my_sell_hint': my_sell_hint,",
        s, count=1
    )
    s = re.sub(
        r"(\.setdefault\('meta',\s*\{\}\)\))",
        r"\1\n        d['meta']['my_buy_hint'] = my_buy_hint\n        d['meta']['my_sell_hint'] = my_sell_hint",
        s
    )

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: pricing hints corregidos")