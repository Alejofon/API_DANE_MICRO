import os
import time
from decimal import Decimal

import psycopg2
from psycopg2.extras import execute_batch

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from zeep import Client
from zeep.transports import Transport
from zeep.exceptions import XMLSyntaxError, TransportError

# ======================================================
# CONFIG
# ======================================================

DATABASE_URL = os.getenv("DATABASE_URL")

WSDL = "http://appweb.dane.gov.co:80/sipsaWS/SrvSipsaUpraBeanService?wsdl"

# ======================================================
# SESSION HTTP ROBUSTA
# ======================================================

session = Session()

retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)

adapter = HTTPAdapter(max_retries=retry_strategy)

session.mount("http://", adapter)
session.mount("https://", adapter)

session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Connection": "keep-alive"
})

transport = Transport(
    session=session,
    timeout=300
)

# ======================================================
# SOAP CLIENT
# ======================================================

print("🚀 Conectando SOAP...")

client = Client(
    wsdl=WSDL,
    transport=transport
)

print("✅ SOAP conectado")

# ======================================================
# DESCARGA CON RETRY
# ======================================================

MAX_RETRIES = 5

result = None

for attempt in range(MAX_RETRIES):

    try:

        print(f"📥 Descargando datos DANE (intento {attempt+1})...")

        result = client.service.promediosSipsaParcial()

        if result:
            print("✅ Datos recibidos correctamente")
            break

    except XMLSyntaxError as e:

        print("❌ XMLSyntaxError:", str(e))

    except TransportError as e:

        print("❌ TransportError:", str(e))

    except Exception as e:

        print("❌ Error general:", str(e))

    wait_time = (attempt + 1) * 10

    print(f"⏳ Esperando {wait_time} segundos...")

    time.sleep(wait_time)

# ======================================================
# VALIDACIÓN
# ======================================================

if not result:
    raise Exception("❌ No fue posible descargar datos del DANE")

print(f"📦 Total registros recibidos: {len(result)}")

# ======================================================
# PROCESAR DATOS
# ======================================================

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

        print("❌ Error procesando fila:", e)

print(f"✅ Filas procesadas: {len(rows)}")

# ======================================================
# POSTGRES
# ======================================================

print("🐘 Conectando PostgreSQL...")

conn = psycopg2.connect(DATABASE_URL)

cur = conn.cursor()

print("✅ PostgreSQL conectado")

# ======================================================
# TABLA
# ======================================================

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

# ======================================================
# LIMPIAR TABLA
# ======================================================

print("🧹 Eliminando datos anteriores...")

cur.execute("TRUNCATE TABLE precios_sipsa")

conn.commit()

# ======================================================
# INSERT MASIVO
# ======================================================

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

# ======================================================
# ÍNDICES
# ======================================================

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

# ======================================================
# FINALIZAR
# ======================================================

cur.close()
conn.close()

print("🏁 ETL FINALIZADO")