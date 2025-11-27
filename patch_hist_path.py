from pathlib import Path
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

# 1) cambiar ruta del histórico
s = s.replace('HIST_FILE   = os.path.join(DATA_DIR, "historico_spreads.json")',
              'HIST_FILE   = os.path.join(DATA_DIR, "historico_spreads_v2.json")')

# 2) loader robusto (ya evita dicts tipo schema_ver)
s = re.sub(
    r"def\s+load_history_last_minutes\([^)]*\):[\s\S]*?^\s*def\s",
    "def load_history_last_minutes(minutes: int = 30) -> pd.DataFrame:\n"
    "    raw = read_json(HIST_FILE, []) or []\n"
    "    if isinstance(raw, dict):\n"
    "        for k in ('rows','data','items','history'): raw = raw.get(k) or raw\n"
    "        raw = raw if isinstance(raw, list) else []\n"
    "    rows = [r for r in raw if isinstance(r, dict)]\n"
    "    if not rows:\n"
    "        return pd.DataFrame(columns=['datetime','asset','spread'])\n"
    "    df = pd.DataFrame.from_records(rows)\n"
    "    if 'datetime' not in df.columns:\n"
    "        return pd.DataFrame(columns=['datetime','asset','spread'])\n"
    "    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce', utc=True)\n"
    "    df = df.dropna(subset=['datetime'])\n"
    "    df['datetime'] = df['datetime'].dt.tz_convert(None)\n"
    "    tmin = pd.Timestamp.utcnow() - pd.Timedelta(minutes=minutes)\n"
    "    df = df[df['datetime'] >= tmin.tz_localize(None)]\n"
    "    keep = [c for c in ('datetime','asset','spread') if c in df.columns]\n"
    "    return df[keep].sort_values('datetime')\n\n"
    "def ",
    s, flags=re.M
)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: dashboard usa historico_spreads_v2.json")