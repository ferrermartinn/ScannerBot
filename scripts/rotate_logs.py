import os, shutil, time, pathlib
LOG_FILE = "scanner.log"
dst_dir = pathlib.Path("logs")
dst_dir.mkdir(parents=True, exist_ok=True)
if not pathlib.Path(LOG_FILE).exists():
    print("No log to rotate.")
    raise SystemExit(0)

ts = time.strftime("%Y%m%d_%H%M%S")
dst = dst_dir / f"scanner_{ts}.log"
# Simple copy then truncate original
shutil.copy2(LOG_FILE, dst)
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")
print("Rotated to", dst)
