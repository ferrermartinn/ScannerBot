from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

INJECT_BARE = r"""
# === Bare-mode guards (auto-inyectado) ===
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    _BARE_MODE = (get_script_run_ctx() is None)
except Exception:
    _BARE_MODE = True

# Si estamos en bare mode, anulamos gráficos para evitar errores de Altair/Narwhals
if _BARE_MODE:
    import streamlit as st
    def _no_chart(*args, **kwargs):
        try:
            # logging mínimo para debug
            print("[bare] altair_chart() suprimido")
        except Exception:
            pass
    try:
        st.altair_chart = _no_chart
    except Exception:
        pass
# === Fin inyección bare-mode ===
"""

# 1) Inyectar guardias tras el import de streamlit
if "get_script_run_ctx" not in s and "BARE_MODE" not in s:
    s = s.replace("import streamlit as st", "import streamlit as st\n" + INJECT_BARE, 1)

# 2) Wrap del llamado de módulo a render_history(...) (línea final)
#    Reemplazamos la invocación directa por un guardia: if not _BARE_MODE: render_history(...)
s = re.sub(
    r"^[ \t]*render_history\([^\n]*\)[ \t]*$",
    "if not (_BARE_MODE if 'BARE_MODE' in globals() else True):\n    render_history(seconds_window=1800)",
    s,
    flags=re.M
)

# 3) Opcional: si quedara algún altair_chart suelto, lo envolvemos con try/except (defensivo)
s = re.sub(
    r"st\.altair_chart\((.+?)\)",
    r"(\n    (lambda: (st.altair_chart(\\1)))() if not (globals().get('_BARE_MODE', True)) else None\n)",
    s
)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: bare-mode guard + altair no-op + render_history guard aplicado")