#!/bin/sh
set -e
cp -f /app/app/service/scanner_p2p.py /app/app/service/scanner_p2p.py.bak 2>/dev/null || true
cp -f /app/scripts/patch_scanner_auto.py /app/scripts/patch_scanner_auto.py.bak 2>/dev/null || true
printf "%s\n" "# neutralized: prevents unwanted rewrites that break indentation" "if __name__ == \"__main__\":" "    pass" > /app/scripts/patch_scanner_auto.py
# (resto igual que el bloque de la opción A)