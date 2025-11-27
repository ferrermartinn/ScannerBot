import os, re, json, sys, py_compile
from pathlib import Path

ROOT = Path("/app")
HELPER_PATH = ROOT / "_merge_helper.py"

HELPER_CODE = r"""
from pathlib import Path
import json, os

_DPATH = Path("/app/data/data.json")

def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def safe_merge_write(new_data: dict):
    # Fusiona sin perder 'assets' ni 'meta' y fuerza schema_ver=2
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

def ensure_helper():
    if not HELPER_PATH.exists():
        HELPER_PATH.write_text(HELPER_CODE, encoding="utf-8")
    # compila para detectar errores sintácticos YA
    py_compile.compile(str(HELPER_PATH), doraise=True)

def patch_file(py: Path) -> bool:
    s = py.read_text(encoding="utf-8", errors="ignore")
    orig = s

    # Asegurar import del helper si vamos a tocar algo
    need_import = False

    # 1) json.dump({...}, open("/app/data/data.json","w"), ...)
    s_new = re.sub(
        r"json\.dump\(\s*(\{[\s\S]*?\})\s*,\s*open\(\s*[\"']/app/data/data\.json[\"']\s*,\s*[\"']w[\"']\s*\)[^)]*\)",
        r"safe_merge_write(\1)", s
    )
    if s_new != s:
        s = s_new
        need_import = True

    # 2) open(...,'w').write(json.dumps({...}))
    s_new = re.sub(
        r"open\(\s*[\"']/app/data/data\.json[\"']\s*,\s*[\"']w[\"']\s*\)\.write\(\s*json\.dumps\(\s*(\{[\s\S]*?\})\s*\)\s*\)",
        r"safe_merge_write(\1)", s
    )
    if s_new != s:
        s = s_new
        need_import = True

    # 3) open(...,'w') a data.json aislado -> comentar (por si quedó algo suelto)
    s = re.sub(
        r"open\(\s*[\"']/app/data/data\.json[\"']\s*,\s*[\"']w[\"']\s*\)",
        r"# replaced_by_safe_merge_write", s
    )

    # Insertar import si hicimos reemplazos
    if need_import and "safe_merge_write(" not in orig:
        lines = s.splitlines()
        ins = 0
        for i, ln in enumerate(lines):
            t = ln.strip()
            if t.startswith("import ") or t.startswith("from "):
                ins = i
            elif ins and t and not t.startswith("#"):
                break
        lines.insert(ins+1, "from _merge_helper import safe_merge_write")
        s = "\n".join(lines)

    if s != orig:
        tmp = py.with_suffix(".tmp")
        tmp.write_text(s, encoding="utf-8")
        py_compile.compile(str(tmp), doraise=True)
        tmp.replace(py)
        return True
    return False

def main():
    ensure_helper()
    touched = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # evitar __pycache__
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in filenames:
            if f.endswith(".py"):
                p = Path(dirpath) / f
                try:
                    if patch_file(p):
                        touched.append(str(p))
                except Exception as e:
                    print(f"[skip]{p}: {e}")
    print("PATCHED_FILES=", len(touched))
    for t in touched:
        print(t)

if __name__ == "__main__":
    main()