# sitecustomize: agrega tradeMethods si están presentes y ya calcula my_suggest_*
import sys, importlib

for p in ("/app", "/app/app"):
    if p not in sys.path:
        sys.path.insert(0, p)

def _to_f(x, d=None):
    try: return float(str(x).replace(",", ""))
    except: return d

def _round2(x):
    try: return float(f"{float(x):.2f}")
    except: return None

def _pick_first8(buyers, sellers):
    b8 = list(buyers or [])[:8]
    s8 = list(sellers or [])[:8]
    cb = max(b8, key=lambda r: _to_f(r.get("price"), 0.0)) if b8 else None
    cs = min(s8, key=lambda r: _to_f(r.get("price"), 1e18)) if s8 else None
    return cb, cs

def _enrich_methods(row):
    if not isinstance(row, dict): 
        return row
    # si ya tiene, listo
    if row.get("tradeMethods") or row.get("tradeMethodsV2"):
        return row
    # heurísticas suaves: algunos builders guardan el original en 'raw' / 'origin' / 'ad'
    for k in ("raw","origin","ad","source","data"):
        base = row.get(k) or {}
        tm = base.get("tradeMethods") or base.get("tradeMethodsV2")
        if tm:
            row = dict(row)
            # normalizar llaves conocidas
            row["tradeMethods"] = tm
            return row
    return row

def _enrich_table(rows):
    out=[]
    for r in rows or []:
        out.append(_enrich_methods(r))
    return out

def _wrap_build(mod):
    for name, fn in list(getattr(mod, "__dict__", {}).items()):
        if callable(fn) and name.startswith("build_") and "view" in name:
            def make_wrapper(orig):
                def _w(*args, **kwargs):
                    view = orig(*args, **kwargs) or {}
                    cfg  = kwargs.get("cfg") or (args[1] if len(args) > 1 else {}) or {}

                    buyers = _enrich_table(view.get("buyers_table")  or [])
                    sellers= _enrich_table(view.get("sellers_table") or [])
                    view["buyers_table"]  = buyers
                    view["sellers_table"] = sellers

                    cb, cs = _pick_first8(buyers, sellers)
                    if cb: view["competitor_buy"]  = _enrich_methods(cb)
                    if cs: view["competitor_sell"] = _enrich_methods(cs)

                    d_abs = _to_f(cfg.get("price_delta_abs"), 0.01) or 0.01
                    d_pct = _to_f(cfg.get("price_delta_pct"), 0.0) or 0.0

                    pb = _to_f((cb or {}).get("price"))
                    ps = _to_f((cs or {}).get("price"))

                    db = max(d_abs, (pb or 0.0) * (d_pct/100.0)) if pb is not None else None
                    ds = max(d_abs, (ps or 0.0) * (d_pct/100.0)) if ps is not None else None

                    buy_hint  = _round2((pb + db) if (pb is not None and db is not None) else None)
                    sell_hint = _round2((ps - ds) if (ps is not None and ds is not None) else None)

                    if buy_hint  is not None: view["my_suggest_buy"]  = buy_hint
                    if sell_hint is not None: view["my_suggest_sell"] = sell_hint

                    view["__debug_hints"] = {
                        "pb": pb, "ps": ps, "d_abs": d_abs, "d_pct": d_pct,
                        "db": db, "ds": ds, "buy_hint": buy_hint, "sell_hint": sell_hint,
                        "cb_nick": (cb or {}).get("nickName"), "cs_nick": (cs or {}).get("nickName"),
                        "buyers_has_methods": any(bool((r or {}).get("tradeMethods") or (r or {}).get("tradeMethodsV2")) for r in buyers),
                        "sellers_has_methods": any(bool((r or {}).get("tradeMethods") or (r or {}).get("tradeMethodsV2")) for r in sellers),
                    }
                    return view
                return _w
            setattr(mod, name, make_wrapper(fn))

try:
    M = importlib.import_module("app.service.scanner_p2p")
    _wrap_build(M)
except Exception as e:
    sys.stderr.write(f"[sitecustomize] error: {e}\n")