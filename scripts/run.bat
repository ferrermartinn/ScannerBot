@echo off
setlocal

REM Ir a la carpeta del script (.bat)
cd /d "%~dp0"

REM (Opcional) activar venv si tenés uno
REM call venv\Scripts\activate.bat

REM Scanner en una ventana
start "Scanner P2P" cmd /k python -u scanner_p2p.py

REM Dashboard en otra ventana (usar -m evita problemas de PATH)
start "Dashboard P2P" cmd /k python -m streamlit run dashboard.py --server.port=8501 --server.headless=true

REM Abrir el navegador
start "" http://localhost:8501

endlocal
