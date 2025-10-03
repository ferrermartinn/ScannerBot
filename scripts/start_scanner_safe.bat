@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
REM Ejecutor no intrusivo para scanner_p2p.py
set PYTHONUTF8=1
REM Opt-in: logging uniforme si existe config/logging.yaml
if exist "config\logging.yaml" (
  set LOG_CFG=config\logging.yaml
)
REM Run
python -X utf8 scanner_p2p.py
