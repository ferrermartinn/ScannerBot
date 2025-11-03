from pathlib import Path, re, sys, py_compile

# TODO: cambia esta ruta según te devolvió el grep (ej: "/app/writer/main.py" o similar)
WRITER_PY = Path("/app/writer/main.py")
s = WRITER_PY.read_text(encoding="utf-8")

INJECT = r"""
# === injected: safe merge writer for data.json ===
from pathlib import Path
import json, os

_DPATH = Path("/app/data/data.json")

def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def safe_merge_write(new_data: dict):
    # Fusiona sobre el archivo existente SIN perder 'assets' ni 'meta'
    cur = _read_json(_DPATH)
    out = dict(cur) if isinstance(cur, dict) else {}

    if isinstance(new_data, dict):
        for k, v in new_data.items():
            if k == "assets" and isinstance(v, dict):
                aset = out.setdefault("assets", {})
                for a, nv in v.items():
                    ev = aset.get(a, {})
                    if isinstance(ev, dict) and isinstance(nv, dict):
                        merged = dict(ev)
                        for kk, vv in nv.items():
                            if kk == "meta" and isinstance(vv, dict):
                                mm = merged.setdefault("meta", {})
                                mm.update(vv)
                            else:
                                merged[kk] = vv
                        aset[a] = merged
                    else:
                        aset[a] = nv
            else:
                out[k] = v

    out.setdefault("schema_ver", 2)
    tmp = _DPATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _DPATH)
"""

# Inyecta helper si no existe
if "def safe_merge_write(" not in s:
    lines = s.splitlines()
    last_imp = 0
    for i, ln in enumerate(lines):
        t = ln.strip()
        if t.startswith("import ") or t.startswith("from "):
            last_imp = i
        elif last_imp and t and not t.startswith("#"):
            break
    lines.insert(last_imp+1, INJECT.strip())
    s = "\n".join(lines)

# Reemplazos típicos de escritura directa -> safe_merge_write
# 1) json.dump({...}, open("/app/data/data.json","w"), …)
s = re.sub(
    r"json\.dump\(\s*(\{[\s\S]*?\})\s*,\s*open\(\s*[\"']/app/data/data\.json[\"']\s*,\s*[\"']w[\"']\s*\)[^)]*\)",
    r"safe_merge_write(\1)",
    s
)

# 2) open(..., "w").write(json.dumps({...}))
s = re.sub(
    r"open\(\s*[\"']/app/data/data\.json[\"']\s*,\s*[\"']w[\"']\s*\)\.write\(\s*json\.dumps\(\s*(\{[\s\S]*?\})\s*\)\s*\)",
    r"safe_merge_write(\1)",
    s
)

# 3) cualquier open(...,'w') a data.json aislado: lo comentamos
s = re.sub(
    r"open\(\s*[\"']/app/data/data\.json[\"']\s*,\s*[\"']w[\"']\s*\)",
    r"# replaced by safe_merge_write",
    s
)

tmp = WRITER_PY.with_suffix(".tmp.py")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(WRITER_PY)
print("OK: writer patched to safe_merge_write")