from pathlib import Path, re
p = Path("/app/app/ui/dashboard.py")
s = p.read_text(encoding="utf-8")

# 1) Localiza el bloque malo que empieza con "\n# injected: meta diag"
m = re.search(r"\\n# injected: meta diag\\ntry:\\n.*?except Exception:\\n\\s*pass\\n", s, re.S)
if m:
    bad = m.group(0)
    good = bad.replace("\\n", "\n")  # convierte \n literales a saltos reales
    s = s.replace(bad, good)

p.write_text(s, encoding="utf-8")
print("OK: meta diag normalizado")