import sys, os, time, logging

LOG_PATH = "/app/logs/writer.log"
os.makedirs("/app/logs", exist_ok=True)

# Config exacta del handler de archivo (evita interferencias de otros loggers)
logger = logging.getLogger()
logger.handlers.clear()
logger.setLevel(logging.INFO)

fh = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8", delay=False)
fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
fh.setFormatter(fmt)
logger.addHandler(fh)

def _append_line(line: str):
    # escritura garantizada incluso si logging fallara
    with open(LOG_PATH, "a", encoding="utf-8", buffering=1) as f:
        f.write(line + "\n")

_append_line("writer boot: inicio (antes de imports del proyecto)")

# IMPORTS DEL PROYECTO (perezosos): si fallan, lo sabremos en el log.
try:
    sys.path.insert(0, "/app")
    from app.service.scanner_p2p import (
        build_asset_view, load_config, DATA_FILE, ASSETS, safe_write_json
    )
    _append_line("writer boot: imports OK")
except Exception as e:
    _append_line(f"writer boot: ERROR importando -> {e!r}")
    raise

while True:
    try:
        cfg = load_config()
        assets = {a: build_asset_view(a, cfg) for a in ASSETS}
        payload = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "fiat": cfg.get("fiat","ARS"),
                   "assets": assets}
        safe_write_json(DATA_FILE, payload)
        msg = f"tick data.json OK {payload['timestamp']}"
        logger.info(msg)
        _append_line(msg)
    except Exception as e:
        logger.exception("writer error: %s", e)
        _append_line(f"writer error: {e!r}")
    time.sleep(15)