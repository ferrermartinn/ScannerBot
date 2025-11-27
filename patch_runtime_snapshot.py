from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

EXTRA = '''
def _write_runtime_snapshot(assets_norm: dict):
    # Escribe /app/data/data_runtime.json con los activos ya normalizados (solo debug/UI).
    import json, os
    RUNTIME = os.path.join(DATA_DIR, "data_runtime.json")
    payload = {"assets": assets_norm}
    tmp = RUNTIME + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, RUNTIME)
'''

if "_write_runtime_snapshot(" not in s:
    s = s.replace("def card_compact(asset: str, info: dict):", EXTRA + "\n\ndef card_compact(asset: str, info: dict):", 1)

# 1) Pinned (expandida): persistimos antes de renderizar
s = s.replace(
    "if pinned and pinned in ASSETS and assets.get(pinned):\n        assets[pinned] = _normalize_asset_for_ui(assets.get(pinned) or {}, cfg)\n        card_expanded(pinned, assets[pinned])",
    "if pinned and pinned in ASSETS and assets.get(pinned):\n        assets[pinned] = _normalize_asset_for_ui(assets.get(pinned) or {}, cfg)\n        _write_runtime_snapshot(assets)\n        card_expanded(pinned, assets[pinned])"
)

# 2) Grid sin pin
s = s.replace(
    "for i, a in enumerate(ASSETS):\n            with cols[i % 2]:\n                assets[a] = _normalize_asset_for_ui(assets.get(a) or {}, cfg)\n                card_compact(a, assets.get(a) or {})",
    "for i, a in enumerate(ASSETS):\n            with cols[i % 2]:\n                assets[a] = _normalize_asset_for_ui(assets.get(a) or {}, cfg)\n                _write_runtime_snapshot(assets)\n                card_compact(a, assets.get(a) or {})"
)

# 3) Otros activos cuando hay pin
s = s.replace(
    "for i, a in enumerate(others):\n                with cols[i % (3 if compact_others else 2)]:\n                    assets[a] = _normalize_asset_for_ui(assets.get(a) or {}, cfg)\n                    card_compact(a, assets.get(a) or {})",
    "for i, a in enumerate(others):\n                with cols[i % (3 if compact_others else 2)]:\n                    assets[a] = _normalize_asset_for_ui(assets.get(a) or {}, cfg)\n                    _write_runtime_snapshot(assets)\n                    card_compact(a, assets.get(a) or {})"
)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: data_runtime.json activado")