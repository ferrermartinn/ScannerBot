from pathlib import Path
import py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

old = 'HIST_FILE   = os.path.join(DATA_DIR, "historico_spreads.json")'
new = 'HIST_FILE   = os.path.join(DATA_DIR, "historico_spreads_v2.json")'
if old in s:
    s = s.replace(old, new)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: HIST_FILE -> historico_spreads_v2.json")