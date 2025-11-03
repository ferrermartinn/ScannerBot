from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

INJECT = r"""
# injected: pandas DataFrame guard for scalar dicts
try:
    import pandas as _pd
    _DF_ORIG = _pd.DataFrame
    def _DF_GUARD(data=None, *args, **kwargs):
        try:
            if isinstance(data, dict):
                # ¿todos escalares? => convertir a una sola fila
                if all(not isinstance(v, (list, tuple, dict, _pd.Series, _pd.Index, _pd.DataFrame)) for v in data.values()):
                    return _DF_ORIG([data], *args, **kwargs)
        except Exception:
            pass
        return _DF_ORIG(data, *args, **kwargs)
    if not getattr(_pd.DataFrame, "__name__", "") == "_DF_GUARD":
        _pd.DataFrame = _DF_GUARD
except Exception:
    pass
"""

# insertar tras los imports
if "pandas DataFrame guard for scalar dicts" not in s:
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

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: DataFrame guard aplicado")