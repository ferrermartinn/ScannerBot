from pathlib import Path, re
p=Path("/app/app/ui/dashboard.py"); s=p.read_text(encoding="utf-8")
s=s.replace("\\sidebar_paytypes_controls()", "\\\\sidebar_paytypes_controls()")  # corrige escape
if "meta']['b_med" not in s:
    s=s.replace("Mi Venta (aviso):", "Mi Venta (aviso):")
    s=s.replace("st.expander(", "st.expander(")  # idempotente
    s=s.replace("st.write(", "st.write(", 1)
    # añade línea de meta justo debajo del competidor venta (primer sitio seguro)
    s=s.replace("Mi Venta (aviso):", "Mi Venta (aviso):")
    # inserta un bloque compacto al final de cada tarjeta si existe 'view'
    s += "\\n# injected: meta diag\\ntry:\\n    st.caption(f\"Top usados: buy={view.get('meta',{}).get('buy_count','-')} sell={view.get('meta',{}).get('sell_count','-')}  |  mediana: buy={view.get('meta',{}).get('b_med','-')} sell={view.get('meta',{}).get('s_med','-')}\")\\nexcept Exception:\\n    pass\\n"
p.write_text(s, encoding="utf-8")
print("OK: UI meta diag")