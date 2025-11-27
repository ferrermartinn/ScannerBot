s=open("/app/app/ui/dashboard.py","r",encoding="utf-8").read()
print("view_get_hits=", s.count("view.get("))
print("tail_preview:\\n", s[-200:])