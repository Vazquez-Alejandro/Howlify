import os
from datetime import datetime
from weasyprint import HTML

def generate_monitor_pdf(uid: str, user_name: str, radar_data: list[dict], kpi: dict) -> bytes:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    rows_html = ""
    for r in radar_data:
        riesgo_color = {"🔴": "#ef4444", "🟠": "#f97316", "🟡": "#eab308", "🟢": "#22c55e", "⚪": "#6b7280"}.get(r.get("riesgo", "⚪"), "#6b7280")
        rows_html += f"""
        <tr>
            <td style="padding:6px 8px;border-bottom:1px solid #eee;color:{riesgo_color};font-size:16px;text-align:center">{r.get("riesgo", "⚪")}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:12px">{r.get("producto", "")}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:12px;text-align:right">${r.get("precio", 0):,.0f}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:12px;text-align:right;color:#ef4444">${r.get("minP", 0):,.0f}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:12px;text-align:right;color:#ef4444">${r.get("maxP", 0):,.0f}</td>
        </tr>"""

    html = f"""
    <html>
    <head><meta charset="utf-8"><style>
        body {{ font-family: 'Helvetica', Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
        h1 {{ color: #111; font-size: 22px; margin-bottom: 4px; }}
        .sub {{ color: #666; font-size: 12px; margin-bottom: 20px; }}
        .kpi-grid {{ display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }}
        .kpi-card {{ background: #f8f8f8; border-radius: 8px; padding: 12px 16px; min-width: 100px; flex: 1; }}
        .kpi-card .val {{ font-size: 20px; font-weight: bold; color: #111; }}
        .kpi-card .label {{ font-size: 10px; color: #888; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #f3f3f3; padding: 8px; font-size: 11px; text-transform: uppercase; color: #555; text-align: left; }}
        td {{ font-size: 12px; }}
        .footer {{ margin-top: 24px; font-size: 10px; color: #aaa; text-align: center; }}
    </style></head>
    <body>
        <h1>🐺 Howlify — Reporte de Monitoreo</h1>
        <p class="sub">Generado el {now} por {user_name}</p>
        <div class="kpi-grid">
            <div class="kpi-card"><div class="val">{kpi.get("total_cazas", 0)}</div><div class="label">Productos</div></div>
            <div class="kpi-card"><div class="val" style="color:#22c55e">{kpi.get("productos_con_precio", 0)}</div><div class="label">Con precio</div></div>
            <div class="kpi-card"><div class="val" style="color:#059669">${kpi.get("ahorro_total", 0):,.0f}</div><div class="label">Ahorro total</div></div>
            <div class="kpi-card"><div class="val" style="color:#eab308">{kpi.get("total_alertas", 0)}</div><div class="label">Alertas</div></div>
            <div class="kpi-card"><div class="val">${kpi.get("precio_promedio", 0):,.0f}</div><div class="label">Precio prom.</div></div>
        </div>
        <table>
            <thead><tr>
                <th style="text-align:center">Riesgo</th><th>Producto</th><th style="text-align:right">Precio</th>
                <th style="text-align:right">MAP Mín</th><th style="text-align:right">MAP Máx</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        <div class="footer">Generado por Howlify — howlify.app</div>
    </body></html>"""

    return HTML(string=html).write_pdf()
