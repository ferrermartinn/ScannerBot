from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

NEW = r"""
def load_history_last_minutes(minutes: int = 30) -> pd.DataFrame:
    # normalized history loader v1
    raw = read_json(HIST_FILE, []) or []
    # Acepta {rows:[...]} o {data:[...]} y filtra tipos erróneos
    if isinstance(raw, dict):
        raw = raw.get("rows") or raw.get("data") or []
    if not isinstance(raw, list) or not raw:
        return pd.DataFrame(columns=["datetime","asset","spread"])
    try:
        df = pd.DataFrame(raw)
    except Exception:
        return pd.DataFrame(columns=["datetime","asset","spread"])
    if "datetime" not in df.columns:
        return pd.DataFrame(columns=["datetime","asset","spread"])
    try:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    except Exception:
        return pd.DataFrame(columns=["datetime","asset","spread"])
    df = df.dropna(subset=["datetime"])
    tmin = pd.Timestamp.utcnow() - pd.Timedelta(minutes=minutes)
    df = df[df["datetime"] >= tmin.tz_localize(None)]
    return df.sort_values("datetime")
"""

# Reemplaza la función completa
pat = re.compile(r"\ndef\s+load_history_last_minutes\([^)]*\):[\s\S]*?\n\ndef\s+", re.M)
m = pat.search(s)
if m:
    s = s[:m.start()] + "\n" + NEW.strip() + "\n\n" + s[m.end()-len("\n\ndef "):]
else:
    # Si no matchea por formato, intenta por el nombre y cierra al final del archivo
    pat2 = re.compile(r"\ndef\s+load_history_last_minutes\([^)]*\):[\s\S]*$", re.M)
    s = pat2.sub("\n"+NEW.strip(), s)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: load_history_last_minutes endurecido")