@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
REM Ejecuta el dashboard Streamlit de forma segura
set PYTHONUTF8=1
if exist "config\logging.yaml" (
  set LOG_CFG=config\logging.yaml
)
streamlit run dashboard.py --server.address=0.0.0.0 --server.headless=true
