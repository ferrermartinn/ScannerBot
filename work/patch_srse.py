import re, pathlib

p = pathlib.Path("/app/app/service/scanner_p2p.py")
t = p.read_text(encoding="utf-8").splitlines()

out = []
rm_log = rm_sr = rm_se = 0

for L in t:
    if re.match(r'^\s*log\.info\(\s*"\[P2P\]\s*spread_raw', L):
        rm_log += 1; continue
    if re.match(r'^\s*sr\s*=', L):
        rm_sr += 1; continue
    if re.match(r'^\s*se\s*=', L):
        rm_se += 1; continue
    out.append(L)

# compacta líneas en blanco duplicadas
res, prev_blank = [], False
for L in out:
    is_blank = (L.strip() == "")
    if is_blank and prev_blank: 
        continue
    prev_blank = is_blank
    res.append(L)

p.write_text("\n".join(res) + "\n", encoding="utf-8")
print({"removed_log": rm_log, "removed_sr": rm_sr, "removed_se": rm_se, "total": rm_log+rm_sr+rm_se})
