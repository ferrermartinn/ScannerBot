from pathlib import Path
import re as _re
import py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

s = _re.sub(
r"def _apply_comp_filters\(rows: list, cfg: dict, assets: dict\) -> list:[\s\S]*?return out",
r"""def _apply_comp_filters(rows: list, cfg: dict, assets: dict) -> list:
    cf = (cfg or {}).get("competitor_filters") or {}
    pozo_min = float(cf.get("pozo_usd_min", 0.0))
    pozo_max = float(cf.get("pozo_usd_max", 10**9))
    min_order_ars = float(cf.get("min_order_ars", 0.0))

    fx = fx_usdt_from_assets(assets or {})
    pozo_min_ars = pozo_min * fx
    pozo_max_ars = pozo_max * fx
    cap_ars = _cap_ars_from_cfg(cfg, assets)

    wanted = set([p.strip().upper() for p in (cfg.get("pay_types") or []) if p.strip()])
    def _has_wanted(trade_methods):
        if not wanted:
            return True
        names = []
        for tm in trade_methods or []:
            n = (tm.get("payMethodName") or tm.get("identifier") or tm.get("tradeMethodName") or "").upper()
            if n: names.append(n)
        return bool(set(names) & wanted)

    out = []
    for r in rows or []:
        try:
            minAmt = as_float(r.get("minAmount"))
            totAmt = as_float(r.get("totalAmount"))
            if minAmt is None or totAmt is None: continue
            if minAmt < min_order_ars: continue
            if not (pozo_min_ars <= totAmt <= pozo_max_ars): continue
            if minAmt > cap_ars: continue
            # solo filtra si existen métodos en la fila
            tms = r.get("tradeMethods") or r.get("tradeMethodsV2") or []
            if tms and not _has_wanted(tms): continue
            out.append(r)
        except Exception:
            continue
    return out""",
s, flags=_re.M)

tmp = P.with_suffix(".tmp"); tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True); tmp.replace(P)
print("OK: filtro pay_types aplicado")