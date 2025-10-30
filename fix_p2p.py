from pathlib import Path
import re, sys, py_compile

SRC = Path("/app/app/service/scanner_p2p.py")

def ensure_typing_import(txt: str) -> str:
    if re.search(r"^\s*from\s+typing\s+import\s+List\b", txt, re.M):
        return txt
    # insertar después del primer bloque de imports
    lines = txt.splitlines()
    insert_at = 0
    for i, ln in enumerate(lines):
        if re.match(r'^\s*(import|from)\s+\w+', ln):
            insert_at = i
        elif insert_at and not re.match(r'^\s*(import|from)\s+\w+', ln):
            break
    lines.insert(insert_at+1, "from typing import List")
    return "\n".join(lines)

def main():
    s = SRC.read_text(encoding="utf-8")

    # Normalizaciones mínimas y seguras
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    # Eliminar NBSP o raros que causan indent
    s = s.replace("\u00A0", " ").replace("\u200B", "")

    start = s.find("def binance_p2p_query(")
    anchor = "# ====== Simulador"
    end   = s.find(anchor, start if start != -1 else 0)

    if start == -1 or end == -1 or end <= start:
        print("ERROR: no encontré la función o el ancla '# ====== Simulador'")
        sys.exit(1)

    new_func = (
        "def binance_p2p_query(asset: str, trade_type: str, fiat: str, pay_types: List[str]) -> List[dict]:\n"
        "    payload = {\n"
        "        \"asset\": asset, \"tradeType\": trade_type, \"fiat\": fiat,\n"
        "        \"page\": 1, \"rows\": 20, \"payTypes\": pay_types or [], \"publisherType\": None\n"
        "    }\n"
        "    try:\n"
        "        r = requests.post(BINANCE_P2P_URL, headers=HEADERS, json=payload, timeout=15)\n"
        "        r.raise_for_status()\n"
        "        d = r.json() or {}\n"
        "        data = d.get(\"data\")\n"
        "        # Formato nuevo: { data: { advList: [...] } }\n"
        "        if isinstance(data, dict):\n"
        "            advs = data.get(\"advList\")\n"
        "            if isinstance(advs, list):\n"
        "                return advs\n"
        "            advs2 = data.get(\"data\")\n"
        "            return advs2 if isinstance(advs2, list) else []\n"
        "        # Formato viejo: { data: [...] }\n"
        "        if isinstance(data, list):\n"
        "            return data\n"
        "        return []\n"
        "    except Exception as e:\n"
        "        log.warning(f\"[P2P] Falla consulta {asset}/{trade_type}: {e}\")\n"
        "        return []\n"
    )

    # Ensamblado: respetar TODO desde el ancla hacia abajo
    prefix = s[:start].rstrip() + "\n\n"
    suffix = s[end:]  # no tocar indent del resto
    s2 = prefix + new_func + "\n\n" + suffix

    s2 = ensure_typing_import(s2)

    # Validar sintaxis antes de escribir
    tmp = SRC.with_suffix(".tmp.py")
    tmp.write_text(s2, encoding="utf-8")
    py_compile.compile(str(tmp), doraise=True)
    tmp.replace(SRC)

    print("OK: función reemplazada, indent normalizada y py_compile OK.")

if __name__ == "__main__":
    main()