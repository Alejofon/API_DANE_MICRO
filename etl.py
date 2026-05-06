import os
from zeep import Client
from zeep.transports import Transport
from requests import Session
import psycopg2
from psycopg2.extras import execute_batch
import json


#=================
# SOAP CONFIG
# =========================

WSDL_URL = "https://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService?wsdl"

print("🚀 Conectando al SOAP del DANE...")

session = Session()

transport = Transport(
    session=session,
    timeout=300
)

client = Client(
    wsdl=WSDL_URL,
    transport=transport
)

# FORZAR endpoint HTTPS
client.service._binding_options["address"] = (
    "https://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService"
)

print("✅ SOAP conectado")

# =========================
# DESCARGAR DATOS
# =========================

print("📥 Descargando datos...")

data = client.service.promediosSipsaParcial()

print("✅ Datos descargados")

print("📦 Tipo:", type(data))

try:
    print("📊 Cantidad registros:", len(data))
except:
    print("⚠️ No se pudo medir longitud")

# Mostrar primeros registros
for i, item in enumerate(data[:5]):
    print(f"\n===== REGISTRO {i+1} =====")
    print(item)

# =========================
# POSTGRES
# =========================

DATABASE_URL = os.getenv("DATABASE_URL")

print("\n🐘 Conectando PostgreSQL...")

conn = psycopg2.connect(DATABASE_URL)

cursor = conn.cursor()

print("✅ PostgreSQL conectado")

# =========================
# CREAR TABLA
# =========================

# =========================
# CREAR TABLA
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS dane_raw (
    id SERIAL PRIMARY KEY,
    data JSONB
)
""")

conn.commit()

print("✅ Tabla lista")

# =========================
# LIMPIAR DATOS ANTERIORES
# =========================

print("🗑️ Eliminando datos anteriores...")

cursor.execute("TRUNCATE TABLE dane_raw RESTART IDENTITY")

conn.commit()

print("✅ Tabla limpiada")

# =========================
# INSERTAR DATOS
# =========================

print("💾 Guardando datos...")

rows = []

for item in data:
    rows.append(
        (json.dumps(item, default=str),)
    )

execute_batch(
    cursor,
    "INSERT INTO dane_raw (data) VALUES (%s)",
    rows,
    page_size=100
)

conn.commit()

print(f"✅ {len(rows)} registros guardados")

cursor.close()
conn.close()

print("🎉 ETL FINALIZADO")