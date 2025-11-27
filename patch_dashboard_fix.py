from pathlib import Path, PurePath
import re, py_compile

P = Path("/app/app/ui/dashboard.py")
s = P.read_text(encoding="utf-8")

# 1) fmt_price con formato ES (miles "." y decimales ",")
s = re.sub(
    r"def\s+fmt_price\([^)]*\):[\s\S]*?^\s*def\s",
    "def fmt_price(x) -> str:\n"
    "    try:\n"
    "        v = float(x)\n"
    "        s = f\"{v:,.2f}\"\n"
    "        # 1,486.45 -> 1.486,45\n"
    "        return s.replace(',', 'X').replace('.', ',').replace('X', '.')\n"
    "    except Exception:\n"
    "        return \"-\"\n\n"
    "def ",  # vuelve a abrir la siguiente def
    s, flags=re.M
)

# 2) load_history_last_minutes con from_records y coerciones seguras
s = re.sub(
    r"def\s+load_history_last_minutes\([^)]*\):[\s\S]*?^\s*def\s",
    "def load_history_last_minutes(minutes: int = 30) -> pd.DataFrame:\n"
    "    raw = read_json(HIST_FILE, []) or []\n"
    "    if isinstance(raw, dict):\n"
    "        for k in ('rows','data','items','history'):\n"
    "            v = raw.get(k)\n"
    "            if isinstance(v, list): raw = v; break\n"
    "        else: raw = []\n"
    "    rows = [r for r in raw if isinstance(r, dict)]\n"
    "    if not rows:\n"
    "        return pd.DataFrame(columns=['datetime','asset','spread'])\n"
    "    try:\n"
    "        df = pd.DataFrame.from_records(rows)\n"
    "    except Exception:\n"
    "        return pd.DataFrame(columns=['datetime','asset','spread'])\n"
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

# 3) eliminar bloque inyectado que usa `view` (warnings Pylance)
s = re.sub(r"\nimport streamlit as st\nst\.sidebar\.caption\([^\n]*\)\n# injected: meta diag[\s\S]*?$", "\nimport streamlit as st\nst.sidebar.caption(\"ScannerBot v0.1.0-beta.1\")\n", s, flags=re.M)

tmp = P.with_suffix(".tmp")
tmp.write_text(s, encoding="utf-8")
py_compile.compile(str(tmp), doraise=True)
tmp.replace(P)
print("OK: dashboard fixed (fmt_price, history loader, remove view block)")