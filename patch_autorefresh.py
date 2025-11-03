from pathlib import Path
p=Path("/app/app/ui/dashboard.py"); s=p.read_text(encoding="utf-8")
if "st.autorefresh(" not in s:
    s = s.replace("st.set_page_config", "st.set_page_config", 1) + \
        "\n# injected: gentle autorefresh\nimport streamlit as st\nst.autorefresh(interval=3000, key=\"refresh\")\n"
p.write_text(s, encoding="utf-8"); print("OK: autorefresh 3s")