from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

# elimina el try/except que usa "view" en la caption "Top usados"
s = re.sub(
    r"\ntry:\s*\n\s*st\.caption\(f\"Top usados:[\s\S]*?\"\)\s*\n\s*except\s+Exception:\s*\n\s*pass\s*",
    "\n# caption diag removida\n",
    s, flags=re.M
)

# por si quedó algún rastro
s = s.replace("view.get(", "# removed view.get(")

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: removido bloque con 'view'")