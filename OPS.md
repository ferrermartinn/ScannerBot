# Operativa Segura — Scanner

## Despliegue/Arranque (Windows)
- **Scanner**: `scripts\start_scanner_safe.bat`
- **Dashboard**: `scripts\start_dashboard_safe.bat`

## Healthcheck
- `python scripts/healthcheck_filesystem.py` (OK si los JSON se actualizan en <= 60s; configurable via `HC_WINDOW_SEC`).

## Logs
- Rotación manual: `python scripts/rotate_logs.py`
- Snapshot de soporte: `python scripts/pack_snapshot.py` (comprime logs + JSON)

## Rollback
- Este overlay sólo agrega archivos. Para volver atrás, borrá lo agregado.
