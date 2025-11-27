import json, os, pandas as pd
p="/app/data/historico_spreads_v2.json"
raw=json.load(open(p)) if os.path.exists(p) else []
df=pd.DataFrame.from_records(raw if isinstance(raw,list) else [raw])
print("shape=", df.shape)
print(df.tail(8))