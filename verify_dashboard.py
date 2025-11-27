import re, json, os, pathlib
P = pathlib.Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

print("helper_existe:", "_apply_my_suggest(" in s)
print("llamada_en_compact:", " _apply_my_suggest(info, load_config())" in s)

m = re.search(r'HIST_FILE\s*=\s*os\.path\.join\(DATA_DIR,\s*"([^"]+)"\)', s)
print("hist_file:", m.group(1) if m else "no encontrado")