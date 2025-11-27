import sys, re
p="/app/app/ui/dashboard.py"
s=open(p,"r",encoding="utf-8").read()
hits=list(re.finditer(r"view\.get\(", s))
print("view_get_hits=", len(hits))