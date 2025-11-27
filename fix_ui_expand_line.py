from pathlib import Path
p = Path("/app/app/ui/dashboard.py")
txt = p.read_text(encoding="utf-8")

lines = txt.splitlines()  # no conserva \n
out = []
changed = False
for ln in lines:
    if "# injected: meta diag" in ln:
        # expandir \n literales a saltos reales SOLO en esta línea
        expanded = ln.replace("\\n", "\n")
        out.extend(expanded.splitlines())
        changed = True
    else:
        out.append(ln)

if changed:
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("OK: línea de meta diag expandida a saltos reales")
else:
    print("Nada que cambiar: no se encontró la línea target")