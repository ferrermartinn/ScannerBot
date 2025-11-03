from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

NEW = r"""
def load_history_last_minutes(minutes: int = 30) -> pd.DataFrame:
    # lector robusto de histórico
    raw = read_json(HIST_FILE, []) or []
    # Acepta list[dict] o dict con {rows|data|items|history:[...]}
    if isinstance(raw, dict):
        for k in ("rows","data","items","history"):
            v = raw.get(k)
            if isinstance(v, list):
                raw = v
                break
        else:
            raw = []
    # Filtrar solo dicts
    rows = [r for r in raw if isinstance(r, dict)]
    if not rows:
        return pd.DataFrame(columns=["datetime","asset","spread"])

    # Construcción segura
    try:
        df = pd.DataFrame.from_records(rows)
    except Exception:
        return pd.DataFrame(columns=["datetime","asset","spread"])

    if "datetime" not in df.columns:
        return pd.DataFrame(columns=["datetime","asset","spread"])

    # Parseo de fechas y ventana móvil
    try:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True).dt.tz_convert(None)
    except Exception:
        return pd.DataFrame(columns=["datetime","asset","spread"])

    df = df.dropna(subset=["datetime"])
    tmin = pd.Timestamp.utcnow() - pd.Timedelta(minutes=minutes)
    df = df[df["datetime"] >= tmin.tz_localize(None)]

    # Orden y columnas mínimas
    keep = [c for c in ("datetime","asset","spread") if c in df.columns]
    df = df[keep].sort_values("datetime")
    return df
"""
# Reemplazo de la función
pat = re.compile(r"\ndef\s+load_history_last_minutes\([^)]*\):[\s\S]*?(?=\n\ndef\s|\n\nclass\s|$)", re.M)
m = pat.search(s)
if m:
    s = s[:m.start()] + "\n" + NEW.strip() + s[m.end():]
else:
    # fallback: inyectar tras imports si no existía
    lines = s.splitlines()
    last_imp = 0
    for i, ln in enumerate(lines):
        t = ln.strip()
        if t.startswith("import ") or t.startswith("from "): last_imp = i
        elif last_imp and t and not t.startswith("#"): break
    lines.insert(last_imp+1, NEW.strip())
    s = "\n".join(lines)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: load_history_last_minutes robusto")