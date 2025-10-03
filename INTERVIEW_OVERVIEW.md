# Project Interview Overview

## Summary
Bot that scans crypto P2P markets, computes spreads, applies liquidity and alert thresholds, and shows everything in a real-time Streamlit dashboard. You can pause, pin assets, and tune margins/volumes persisted in `config.json`. Runs as CLI or dashboard. Dockerized and validated by CI.

## Tech stack, usage, and notes

- **Python 3.12**  
  Used as the core language. Modules under `app/{service,core,ui}`.  
  Notes: package layout with `__init__.py` avoided import errors.

- **Requests**  
  Used for HTTP to P2P price sources.  
  Notes: timeouts/retries kept simple; IO isolated in `service`.

- **Pandas / NumPy**  
  Used for cleaning and spread calculations.  
  Notes: vectorized ops to keep UI responsive.

- **Streamlit**  
  Used in `app/ui/dashboard.py` for metrics, tables, and controls.  
  Notes: first-run email prompt handled; removed legacy `bandit_ui` import.

- **Custom “bandit” module**  
  Used for simple prioritization heuristics (e.g., `DeltaBandit`).  
  Notes: moved to `app/service/bandit/` and fixed import paths.

- **Config persistence (`config.json`)**  
  Helpers in `app/core/config.py`, safe write with temp file, deep-merge defaults.  
  Notes: stores pause, mute, margins, per-alert volumes, per-asset thresholds.

- **Alert sounds**  
  `app/service/sonidos.py` respects `mute` and per-alert volume.  
  Notes: decoupled from UI.

- **Pytest**  
  Basic smoke tests in `tests/`.  
  Notes: foundation ready for synthetic market fixtures.

- **GitHub Actions (CI)**  
  Workflow installs deps, runs lint/format (non-blocking) and smoke tests.  
  Notes: first run failed due to strict checks; relaxed to keep green.

- **Docker + Docker Compose**  
  `Dockerfile` and `docker-compose.yml` for dashboard and scanner services.  
  Notes: fixed `requirements.txt` heredoc issue; WSL2 and PATH setup on Windows.

- **Repo hygiene**  
  `.gitignore` excludes local artifacts; `example.env` provided.  
  Notes: prevents leaking local data and noise in PRs.

- **Docs & release**  
  `README`, `CHANGELOG`, `LICENSE`, CI badge, `v0.1.0` tag.  
  Notes: interview-ready presentation and reproducible run.

## Lessons and next steps
- Start with package structure and CI to avoid friction later.  
- Add integration tests with synthetic market data and alert paths.  
- Expose Prometheus metrics and HTTP healthcheck.  
- Add Telegram alerts and per-asset ARS risk caps.
