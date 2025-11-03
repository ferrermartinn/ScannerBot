from pathlib import Path
import json, os, pandas as pd

# Cargar el histórico
p = "/app/data/historico_spreads.json"
raw = json.load(open(p)) if os.path.exists(p) else []

# Usamos from_records para asegurarnos de que los datos escalares se manejen bien
try:
    if isinstance(raw, list):
        df = pd.DataFrame.from_records(raw)
    else:
        df = pd.DataFrame.from_records([raw])
    print("DataFrame creado con éxito")
except Exception as e:
    print("Error al crear DataFrame", e)

# Verifica el contenido de la variable df
print(df.head())