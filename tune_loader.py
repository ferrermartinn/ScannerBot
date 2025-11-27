from pathlib import Path, re
p = Path("/app/app/ui/dashboard.py"); s = p.read_text(encoding="utf-8")
# max_tries: 3->6, delay: 0.15->0.20
s = re.sub(r"def _safe_read_json\(max_tries: int = \d+, delay: float = [0-9.]+\):",
           "def _safe_read_json(max_tries: int = 6, delay: float = 0.20):", s)
p.write_text(s, encoding="utf-8"); print("OK: loader tuned")