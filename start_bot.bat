@echo off
echo Starting Docker...
docker compose up -d

echo Verifying containers...
docker compose ps

echo Starting writer in background...
docker compose exec scanner sh -lc "nohup python -u /app/app/writer_log.py > /dev/null 2>&1 & echo \$! > /tmp/w_writer.pid"

echo All set! The bot is running in the background.
pause
