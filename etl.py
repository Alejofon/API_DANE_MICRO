import requests
import xml.etree.ElementTree as ET
import psycopg2
from psycopg2.extras import execute_batch
from decimal import Decimal
from datetime import datetime
import os

# =========================
# CONFIG
# =========================

DATABASE_URL = os.getenv("DATABASE_URL")

SOAP_URL = "http://appweb.dane.gov.co:80/sipsaWS/SrvSipsaUpraBeanService"

HEADERS = {
    "Content-Type": "text/xml;charset=UTF-8",
    "SOAPAction": ""
}

SOAP_BODY = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ser="http://servicios.sipsa.co.gov.dane/">

   <soapenv:Header/>

   <soapenv:Body>
      <ser:promediosSipsaParcial/>
   </soapenv:Body>

</soapenv:Envelope>
"""

# =========================
# DESCARGA SOAP
# =========================

print("🚀 Descargando datos del DANE...")

response = requests.post(
    SOAP_URL,
    data=SOAP_BODY,
    headers=HEADERS,
    timeout=300
)

print("✅ STATUS:", response.status_code)

xml_content = response.text

if response.status_code != 200:
    print(xml_content)
    raise Exception("Error consultando SOAP")

# =========================
# PARSE XML
# =========================

ns = {
    "soap": "http://schemas.xmlsoap.org/soap/envelope/"
}

root = ET.fromstring(xml_content)

# =========================
# EXTRAER ITEMS
# =========================

rows = []

for item in root.iter():

    data = {}

    for child in item:
        tag = child.tag.split("}")[-1]
        value = child.text

        data[tag] = value

    # solo procesar registros válidos
    if "artiNombre" not in data:
        continue

    try:

        fecha = None

        if data.get("enmaFecha"):
            fecha = datetime.fromisoformat(
                data["enmaFecha"].replace("Z", "+00:00")
            ).date()

        row = (
            data.get("artiNombre"),
            data.get("grupNombre"),
            data.get("muniNombre"),
            data.get("deptNombre"),
            data.get("fuenNombre"),
            fecha,
            Decimal(data.get("minimoKg", "0")),
            Decimal(data.get("maximoKg", "0")),
            Decimal(data.get("promedioKg", "0"))
        )

        rows.append(row)

    except Exception as e:
        print("❌ Error procesando fila:", e)

print(f"📦 Registros procesados: {len(rows)}")

# =========================
# POSTGRES
# =========================

conn = psycopg2.connect(DATABASE_URL)

cur = conn.cursor()

# =========================
# CREAR TABLA
# =========================

cur.execute("""
CREATE TABLE IF NOT EXISTS precios_sipsa (

    id SERIAL PRIMARY KEY,

    articulo TEXT,
    grupo TEXT,

    ciudad TEXT,
    departamento TEXT,

    fuente TEXT,

    fecha DATE,

    precio_min NUMERIC,
    precio_max NUMERIC,
    precio_promedio NUMERIC
)
""")

conn.commit()

# =========================
# LIMPIAR TABLA
# =========================

print("🧹 Eliminando datos anteriores...")

cur.execute("TRUNCATE TABLE precios_sipsa")

conn.commit()

# =========================
# INSERT MASIVO
# =========================

print("⬆️ Insertando registros...")

execute_batch(
    cur,
    """
    INSERT INTO precios_sipsa (

        articulo,
        grupo,
        ciudad,
        departamento,
        fuente,
        fecha,
        precio_min,
        precio_max,
        precio_promedio

    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,
    rows,
    page_size=1000
)

conn.commit()

print("✅ Carga completada")

# =========================
# CERRAR
# =========================

cur.close()
conn.close()

print("🏁 ETL FINALIZADO")