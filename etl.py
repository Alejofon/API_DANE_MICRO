from zeep import Client
from zeep.transports import Transport
from requests import Session
import psycopg2
from psycopg2.extras import execute_batch
from decimal import Decimal
from datetime import datetime
import os

# ==========================================
# CONFIG
# ==========================================

DATABASE_URL = os.getenv("DATABASE_URL")

WSDL = "http://appweb.dane.gov.co:80/sipsaWS/SrvSipsaUpraBeanService?wsdl"

# ==========================================
# SOAP CLIENT
# ==========================================

print("🚀 Conectando SOAP...")

session = Session()

transport = Transport(session=session, timeout=300)

client = Client(
    wsdl=WSDL,
    transport=transport
)

print("✅ SOAP conectado")

# ==========================================
# DESCARGAR DATOS
# ==========================================

print("📥 Descargando datos DANE...")

result = client.service.promediosSipsaParcial()

print("✅ Datos recibidos")

if not result:
    raise Exception("❌ No llegaron datos")

print(f"📦 Total registros: {len(result)}")

# ==========================================
# PROCESAR
# ==========================================

rows = []

for item in result:

    try:

        fecha = None

        if item.enmaFecha:
            fecha = item.enmaFecha.date()

        row = (

            str(item.artiNombre) if item.artiNombre else None,
            str(item.grupNombre) if item.grupNombre else None,

            str(item.muniNombre) if item.muniNombre else None,
            str(item.deptNombre) if item.deptNombre else None,

            str(item.fuenNombre) if item.fuenNombre else None,

            fecha,

            Decimal(item.minimoKg) if item.minimoKg else 0,
            Decimal(item.maximoKg) if item.maximoKg else 0,
            Decimal(item.promedioKg) if item.promedioKg else 0

        )

        rows.append(row)

    except Exception as e:
        print("❌ Error fila:", e)

print(f"✅ Filas procesadas: {len(rows)}")

# ==========================================
# POSTGRES
# ==========================================

print("🐘 Conectando PostgreSQL...")

conn = psycopg2.connect(DATABASE_URL)

cur = conn.cursor()

print("✅ PostgreSQL conectado")

# ==========================================
# TABLA
# ==========================================

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

# ==========================================
# LIMPIAR DATOS ANTERIORES
# ==========================================

print("🧹 Eliminando datos anteriores...")

cur.execute("TRUNCATE TABLE precios_sipsa")

conn.commit()

# ==========================================
# INSERT MASIVO
# ==========================================

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

    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,
    rows,
    page_size=1000
)

conn.commit()

print("✅ Datos insertados")

# ==========================================
# ÍNDICES
# ==========================================

print("⚡ Creando índices...")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_articulo
ON precios_sipsa(articulo)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_ciudad
ON precios_sipsa(ciudad)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_fecha
ON precios_sipsa(fecha)
""")

conn.commit()

# ==========================================
# CERRAR
# ==========================================

cur.close()
conn.close()

print("🏁 ETL FINALIZADO")