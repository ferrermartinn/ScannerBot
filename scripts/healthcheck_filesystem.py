import os, time, json, sys, pathlib

WINDOW_SECONDS = int(os.getenv("HC_WINDOW_SEC", "60"))
base = pathlib.Path(".")
targets = [
    ("scanner_data.json", "json"),
    ("historico_spreads.json", "json"),
    ("scanner.log", "log"),
]
now = time.time()
ok_files = []
stale = []

for fname, ftype in targets:
    p = base / fname
    if not p.exists():
        continue
    mtime = p.stat().st_mtime
    age = now - mtime
    if age <= WINDOW_SECONDS:
        ok_files.append((fname, round(age,1)))
    else:
        stale.append((fname, round(age,1)))

# Healthy si al menos uno de los JSON se actualizó dentro de la ventana
json_recent = any(n == "scanner_data.json" and age <= WINDOW_SECONDS for (n, age) in ok_files) or               any(n == "historico_spreads.json" and age <= WINDOW_SECONDS for (n, age) in ok_files)

if json_recent:
    print("OK", ok_files)
    sys.exit(0)
else:
    print("STALE", stale or "no targets")
    sys.exit(1)
