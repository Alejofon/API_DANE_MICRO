# pruebas_validacion/evidencia_etl.py
"""
Evidencia del ETL diario de precios DANE/SIPSA: consulta la tabla
dane_normalizado en PostgreSQL y reporta el número de registros, la fecha
máxima de datos y una muestra reciente. Requiere DATABASE_URL (en .env).

Salida: resultados/evidencia_etl.md  y  resultados/evidencia_etl.json
"""

import os

from common import guardar_json, guardar_texto, ahora_iso


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    except Exception:
        pass

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        guardar_texto("evidencia_etl.md", "# Evidencia ETL\n\nNo hay DATABASE_URL configurada.")
        print("⚠️ DATABASE_URL no configurada; no se pudo consultar la base.")
        return

    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(database_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT COUNT(*) AS total, MAX(enma_fecha) AS fecha_max, MIN(enma_fecha) AS fecha_min FROM dane_normalizado")
    resumen = cur.fetchone()

    cur.execute("SELECT COUNT(DISTINCT arti_nombre) AS articulos, COUNT(DISTINCT dept_nombre) AS departamentos FROM dane_normalizado")
    distintos = cur.fetchone()

    cur.execute("""
        SELECT arti_nombre, dept_nombre, promedio_kg, enma_fecha
        FROM dane_normalizado ORDER BY enma_fecha DESC LIMIT 8
    """)
    muestra = cur.fetchall()

    cur.close()
    conn.close()

    datos = {
        "total_registros": resumen["total"],
        "fecha_max": str(resumen["fecha_max"]),
        "fecha_min": str(resumen["fecha_min"]),
        "articulos_distintos": distintos["articulos"],
        "departamentos_distintos": distintos["departamentos"],
        "muestra_reciente": [
            {"articulo": m["arti_nombre"], "departamento": m["dept_nombre"],
             "precio_kg": float(m["promedio_kg"]) if m["promedio_kg"] is not None else None,
             "fecha": str(m["enma_fecha"])}
            for m in muestra
        ],
    }
    guardar_json("evidencia_etl.json", datos)

    md = [
        f"# Evidencia del ETL DANE/SIPSA — {ahora_iso()}", "",
        f"- **Registros en `dane_normalizado`:** {datos['total_registros']:,}",
        f"- **Rango de fechas:** {datos['fecha_min']} → **{datos['fecha_max']}** (fecha máxima)",
        f"- **Artículos distintos:** {datos['articulos_distintos']}",
        f"- **Departamentos (centrales mayoristas) distintos:** {datos['departamentos_distintos']}",
        "",
        "**Muestra reciente:**", "",
        "| Artículo | Departamento | Precio/kg (COP) | Fecha |",
        "|---|---|--:|---|",
    ]
    for m in datos["muestra_reciente"]:
        md.append(f"| {m['articulo']} | {m['departamento']} | {m['precio_kg']} | {m['fecha']} |")
    md += ["", "> El ETL se ejecuta a diario mediante un workflow de GitHub Actions "
           "(`.github/workflows/etl.yml`) que corre `etl.py` contra el SOAP oficial del DANE."]
    guardar_texto("evidencia_etl.md", "\n".join(md))
    print(f"✅ Evidencia ETL: {datos['total_registros']:,} registros, fecha máx {datos['fecha_max']}")


if __name__ == "__main__":
    main()
