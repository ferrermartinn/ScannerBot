from pathlib import Path; import re, py_compile
P = Path("/app/app/ui/dashboard.py"); s = P.read_text(encoding="utf-8")

# elimina cualquier bloque que haga referencia a la variable 'view' en las últimas líneas
s = re.sub(r"\nimport streamlit as st\s*?\nst\.sidebar\.caption\([^\n]*\)\s*?\n# injected: meta diag[\s\S]*?\Z",
           "\nimport streamlit as st\nst.sidebar.caption(\"ScannerBot v0.1.0-beta.1\")\n", s, flags=re.M)

tmp = P.with_suffix(".tmp"); tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True); tmp.replace(P)
print("OK: bloque 'view' removido")