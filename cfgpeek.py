import sys, json
sys.path.insert(0, "/app")
from app.service.scanner_p2p import load_config
print(json.dumps(load_config(), ensure_ascii=False, indent=2))