![ci](https://github.com/ferrermartinn/ScannerBot/actions/workflows/ci.yml/badge.svg)
# 🪙 P2P Arbitrage Scanner

Herramienta en Python para escanear oportunidades de arbitraje en mercados P2P de criptomonedas. Incluye lógica automatizada de análisis y un dashboard interactivo con Streamlit para monitoreo en tiempo real.

---

## 🚀 Características principales
- Escaneo continuo de spreads y liquidez en mercados P2P.
- Configuración dinámica desde archivo `config.json`.
- Interfaz visual en tiempo real con métricas, tablas y logs.
- Estructura modular lista para producción.
- Fácil despliegue en local o servidor (Docker próximamente).

---

## 🛠️ Requisitos

- Python **3.12+**
- Git
- PowerShell o Bash
- Cuenta en Binance u otro exchange (opcional para datos reales)

---

## 📦 Instalación

Cloná el repositorio y configurá el entorno:

```bash
git clone https://github.com/<tu_usuario>/<tu_repo>.git
cd <tu_repo>

# Crear entorno virtual
python -m venv .venv

# Activar entorno (PowerShell)
.\.venv\Scripts\Activate.ps1
# o (Linux/Mac)
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

