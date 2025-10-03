
from pathlib import Path
import re, textwrap

FN = "scanner_p2p.py"

p = Path(FN)
code = p.read_text(encoding="utf-8", errors="ignore")

changed = False

# 1) Ensure deque import
if "from collections import deque" not in code:
    m = re.search(r"^(import .*\n)+", code, re.M)
    if m:
        code = code[:m.end()] + "from collections import deque\n" + code[m.end():]
    else:
        code = "from collections import deque\n" + code
    changed = True

# 2) Add detect_regime_auto helpers
if "def detect_regime_auto(" not in code:
    helper = textwrap.dedent('''
    # === Régimen automático: detector simple de dumping vs estable ===
    _REG = {"regime": "stable", "t0": 0.0}
    _WIN = deque(maxlen=12)  # ~60s si el loop refresca cada 5s

    def detect_regime_auto(top_buy, top_sell, now, cfg: dict) -> str:
        pos = cfg.get("positioning", {}) or {}
        win_s    = float(pos.get("window_s", 60))
        thr_drop = float(pos.get("dumping_drop_pct", 0.006))  # 0.6%
        debounce = float(pos.get("debounce_s", 45))

        if top_buy and top_sell:
            mid = (float(top_buy) + float(top_sell)) / 2.0
            _WIN.append((now, mid))

        if len(_WIN) < 6:
            return _REG["regime"]

        t0, p0 = _WIN[0]
        t1, p1 = _WIN[-1]
        if (t1 - t0) < win_s or p0 <= 0:
            return _REG["regime"]

        drop = max(0.0, (p0 - p1) / p0)
        want = "dumping" if drop >= thr_drop else "stable"

        if want != _REG["regime"] and (now - _REG.get("t0", 0)) >= debounce:
            _REG["regime"] = want
            _REG["t0"] = now
        return _REG["regime"]
    ''')
    # Prefer to place after bandit helpers if present
    anchor = "def bandit_quote("
    pos = code.find(anchor)
    if pos != -1:
        end = code.find("\n# ==== end helpers", pos)
        insert_at = end if end != -1 else pos
        code = code[:insert_at] + "\n" + helper + "\n" + code[insert_at:]
    else:
        code = code + "\n" + helper + "\n"
    changed = True

# 3) Wrap the bandit_quote call to update regime
pattern = r"b_buy,\s*b_sell,\s*d_buy,\s*d_sell\s*=\s*bandit_quote\(\s*asset\s*,\s*cfg\s*,\s*top_buyer_price\s*,\s*top_seller_price\s*,\s*\{\s*\"imbalance\"\s*:\s*0\.0\s*\}\s*\)"
if re.search(pattern, code):
    repl = textwrap.dedent('''
    # actualizar régimen
    now_ts = time.time()
    reg_mode = str((cfg.get("positioning") or {}).get("regime", "stable")).lower()
    if reg_mode == "auto":
        reg_mode = detect_regime_auto(top_buyer_price, top_seller_price, now_ts, cfg)
    cfg.setdefault("positioning", {})["regime"] = reg_mode

    b_buy, b_sell, d_buy, d_sell = bandit_quote(asset, cfg, top_buyer_price, top_seller_price, {"imbalance": 0.0})
    ''')
    code = re.sub(pattern, repl, code)
    changed = True
else:
    # try a generic bandit_quote call
    alt = re.search(r"bandit_quote\(asset,\s*cfg,\s*top_buyer_price,\s*top_seller_price,\s*\{[^}]*\}\)", code)
    if alt:
        start = alt.start()
        call  = code[alt.start():alt.end()]
        wrapper = textwrap.dedent('''
        # actualizar régimen
        now_ts = time.time()
        reg_mode = str((cfg.get("positioning") or {}).get("regime", "stable")).lower()
        if reg_mode == "auto":
            reg_mode = detect_regime_auto(top_buyer_price, top_seller_price, now_ts, cfg)
        cfg.setdefault("positioning", {})["regime"] = reg_mode

        ''') + call
        code = code[:start] + wrapper + code[alt.end():]
        changed = True

if changed:
    p.write_text(code, encoding="utf-8")
    print("OK: parche aplicado a", FN)
else:
    print("Nada que cambiar: patrones no encontrados en", FN)
