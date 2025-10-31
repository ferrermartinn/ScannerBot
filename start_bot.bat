@echo off
echo Starting ScannerBot (scanner + dashboard + writer)...
docker compose -f docker-compose.yml -f docker-compose.writer.yml up -d --build

echo Waiting writer health...
for /l %%i in (1,1,20) do (
  docker compose -f docker-compose.yml -f docker-compose.writer.yml ps | findstr /i "writer" | findstr /i "healthy" >nul && goto OK
  timeout /t 2 >nul
)
echo Writer no healthy aun. Continuo igual...

:OK
start http://localhost:8501
echo Listo. Presiona una tecla para salir.
pause >nul
