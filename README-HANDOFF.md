# Handoff UI History Beta 1
Rama: handoff/ui-history-beta1 | Tag: handoff-2025-11-03

Objetivo: revisar UI (histórico de spreads + gráfico + sidebar status + filtros de pago)
Entrada principal: app/ui/dashboard.py
Cómo correr: docker compose up -d
Datos: /app/data/data.json y /app/data/historico_spreads_v2.json

Pedir: cleanup de imports duplicados y tests para load_history_last_minutes()