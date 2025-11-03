from pathlib import Path
import sys, re, py_compile

SRC = Path("/app/app/service/scanner_p2p.py")
code = SRC.read_text(encoding="utf-8")

NEW_FUNC = r"""
def safe_write_json(path, data):
    from pathlib import Path
    import json, os

    p = Path(path)
    try:
        cur = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        cur = {}

    out = dict(cur) if isinstance(cur, dict) else {}

    if isinstance(data, dict):
        for k, v in data.items():
            if k == "assets" and isinstance(v, dict):
                aset = out.setdefault("assets", {})
                for a, nv in v.items():
                    ev = aset.get(a, {})
                    if isinstance(ev, dict) and isinstance(nv, dict):
                        merged = dict(ev)
                        # merge superficial de nivel asset
                        for kk, vv in nv.items():
                            if kk == "meta" and isinstance(vv, dict):
                                mm = merged.setdefault("meta", {})
                                mm.update(vv)  # nunca borrar meta existente
                            else:
                                merged[kk] = vv
                        aset[a] = merged
                    else:
                        aset[a] = nv
            else:
                out[k] = v

    out.setdefault("schema_ver", 2)

    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)
"""

# reemplaza la definición existente de safe_write_json por NEW_FUNC
pattern = r"\ndef\s+safe_write_json\s*\([^)]*\):[\s\S]*?(?=\n\ndef\s|\n\nclass\s|$)"
m = re.search(pattern, code)
if m:
    code = code[:m.start()] + "\n" + NEW_FUNC.strip() + code[m.end():]
else:
    # si no existe, la inyectamos tras los imports
    lines = code.splitlines()
    last_imp = 0
    for i, ln in enumerate(lines):
        t = ln.strip()
        if t.startswith("import ") or t.startswith("from "):
            last_imp = i
        elif last_imp and t and not t.startswith("#"):
            break
    lines.insert(last_imp+1, NEW_FUNC.strip())
    code = "\n".join(lines)

tmp = SRC.with_suffix(".tmp.py")
tmp.write_text(code, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(SRC)
print("OK: safe_write_json ahora hace merge y preserva meta + schema_ver")