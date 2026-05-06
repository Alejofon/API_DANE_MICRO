import os
from zeep import Client
from zeep.transports import Transport
from requests import Session
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import re
import json

# =========================
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
print("📊 Cantidad registros:", len(data))

# =========================
# INSPECCIONAR ESTRUCTURA
# =========================

print("\n🔍 Inspeccionando estructura del primer registro...")

if len(data) > 0:
    primer_registro = data[0]
    print("Tipo del registro:", type(primer_registro))
    print("Atributos disponibles:", dir(primer_registro))
    print("\n--- Contenido (intentando varias formas) ---")
    
    # Intentar diferentes formas de acceder a los datos
    print("\n1. Como string:", str(primer_registro))
    print("\n2. Como dict:", vars(primer_registro) if hasattr(primer_registro, '__dict__') else "No tiene __dict__")
    
    # Intentar acceder como si fuera un objeto
    print("\n3. Intentando acceder a artiNombre directamente:")
    try:
        print("   artiNombre:", primer_registro.artiNombre)
    except:
        print("   No se pudo acceder a artiNombre")
    
    # Mostrar todos los atributos que no sean métodos
    print("\n4. Atributos no métodos:")
    for attr in dir(primer_registro):
        if not attr.startswith('_') and not callable(getattr(primer_registro, attr)):
            try:
                value = getattr(primer_registro, attr)
                print(f"   {attr}: {value} (tipo: {type(value)})")
            except:
                print(f"   {attr}: error al leer")

# =========================
# POSTGRES CONNECTION
# =========================

DATABASE_URL = os.getenv("DATABASE_URL")

print("\n🐘 Conectando PostgreSQL...")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("✅ PostgreSQL conectado")

# =========================
# FUNCIONES DE LIMPIEZA
# =========================

def limpiar_numero(valor):
    """Convierte Decimal o string a float"""
    if valor is None:
        return None
    try:
        # Si es Decimal o similar, convertir a string primero
        valor_str = str(valor).strip()
        # Eliminar asteriscos
        valor_str = valor_str.replace('*', '')
        if valor_str:
            return float(valor_str)
        return None
    except (ValueError, TypeError):
        return None

def limpiar_texto(valor):
    """Limpia texto"""
    if valor is None:
        return None
    return str(valor).strip().replace('*', '').strip()

def convertir_fecha(valor):
    """Convierte fecha"""
    if valor is None:
        return None
    try:
        # Si es datetime de Zeep
        if hasattr(valor, 'date'):
            return valor.date()
        # Si es string
        if isinstance(valor, str):
            return datetime.strptime(valor, '%Y-%m-%d').date()
        return valor
    except:
        return None

# =========================
# EXTRAER DATOS CORRECTAMENTE
# =========================

print("\n🔄 Extrayendo y normalizando datos...")

# Lista de campos esperados según tu ejemplo
CAMPOS = [
    'artiNombre', 'deptNombre', 'enmaFecha', 'fuenId', 'fuenNombre',
    'futiId', 'grupNombre', 'idArtiSemana', 'maximoKg', 'minimoKg',
    'muniId', 'muniNombre', 'promedioKg'
]

rows_normalizados = []
errores = 0
muestra_vacia = True

for idx, item in enumerate(data):
    try:
        # Crear diccionario vacío
        registro = {}
        
        # Método 1: Si es objeto zeep, usar los atributos
        for campo in CAMPOS:
            try:
                valor = getattr(item, campo, None)
                if valor is not None:
                    registro[campo] = valor
            except:
                pass
        
        # Método 2: Si tiene __dict__ (objeto normal)
        if hasattr(item, '__dict__') and not registro:
            registro = item.__dict__
        
        # Método 3: Si es dict directamente
        if isinstance(item, dict) and not registro:
            registro = item
        
        # Si aún está vacío, intentar convertir a dict
        if not registro:
            registro = vars(item) if hasattr(item, '__vars__') else {}
        
        # Mostrar un registro para depuración
        if muestra_vacia and registro:
            print(f"\n✅ Registro {idx} extraído correctamente:")
            for key, value in registro.items():
                print(f"   {key}: {value} (tipo: {type(value)})")
            muestra_vacia = False
        
        # Extraer valores (usando get con nombres alternativos)
        arti_nombre = limpiar_texto(registro.get('artiNombre') or registro.get('artinombre'))
        dept_nombre = limpiar_texto(registro.get('deptNombre') or registro.get('deptnombre'))
        enma_fecha = convertir_fecha(registro.get('enmaFecha') or registro.get('enmafecha'))
        fuen_id = registro.get('fuenId') or registro.get('fuenid')
        fuen_id = int(fuen_id) if fuen_id is not None else None
        fuen_nombre = limpiar_texto(registro.get('fuenNombre') or registro.get('fuennombre'))
        futi_id = registro.get('futiId') or registro.get('futiid')
        futi_id = int(futi_id) if futi_id is not None else None
        grup_nombre = limpiar_texto(registro.get('grupNombre') or registro.get('grupnombre'))
        id_arti_semana = registro.get('idArtiSemana') or registro.get('idartisemana')
        id_arti_semana = int(id_arti_semana) if id_arti_semana is not None else None
        maximo_kg = limpiar_numero(registro.get('maximoKg') or registro.get('maximokg'))
        minimo_kg = limpiar_numero(registro.get('minimoKg') or registro.get('minimokg'))
        muni_id = limpiar_texto(registro.get('muniId') or registro.get('muniid'))
        muni_nombre = limpiar_texto(registro.get('muniNombre') or registro.get('muninombre'))
        promedio_kg = limpiar_numero(registro.get('promedioKg') or registro.get('promediokg'))
        
        # Validar que al menos tenga algún dato significativo
        if arti_nombre or dept_nombre or promedio_kg:
            row = (
                arti_nombre,
                dept_nombre,
                enma_fecha,
                fuen_id,
                fuen_nombre,
                futi_id,
                grup_nombre,
                id_arti_semana,
                maximo_kg,
                minimo_kg,
                muni_id,
                muni_nombre,
                promedio_kg
            )
            rows_normalizados.append(row)
        else:
            errores += 1
            if errores <= 3:  # Mostrar solo primeros errores
                print(f"⚠️ Registro {idx} vacío: {registro}")
        
    except Exception as e:
        errores += 1
        if errores <= 5:
            print(f"⚠️ Error en registro {idx}: {e}")
        continue

print(f"\n📊 Resumen de extracción:")
print(f"   Registros totales: {len(data)}")
print(f"   Registros válidos: {len(rows_normalizados)}")
print(f"   Registros vacíos/error: {errores}")

# =========================
# CREAR Y LLENAR TABLA
# =========================

print("\n📋 Creando tabla normalizada...")

# Eliminar tabla si existe
cursor.execute("DROP TABLE IF EXISTS dane_normalizado CASCADE")

# Crear tabla
cursor.execute("""
CREATE TABLE dane_normalizado (
    id SERIAL PRIMARY KEY,
    arti_nombre VARCHAR(200),
    dept_nombre VARCHAR(100),
    enma_fecha DATE,
    fuen_id INTEGER,
    fuen_nombre VARCHAR(200),
    futi_id INTEGER,
    grup_nombre VARCHAR(100),
    id_arti_semana INTEGER,
    maximo_kg NUMERIC(12,2),
    minimo_kg NUMERIC(12,2),
    muni_id VARCHAR(20),
    muni_nombre VARCHAR(200),
    promedio_kg NUMERIC(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
print("✅ Tabla creada")

# =========================
# INSERTAR DATOS
# =========================

if rows_normalizados:
    print("\n💾 Insertando datos normalizados...")
    
    execute_batch(
        cursor,
        """
        INSERT INTO dane_normalizado 
        (arti_nombre, dept_nombre, enma_fecha, fuen_id, fuen_nombre, 
         futi_id, grup_nombre, id_arti_semana, maximo_kg, minimo_kg, 
         muni_id, muni_nombre, promedio_kg)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows_normalizados,
        page_size=500
    )
    
    conn.commit()
    print(f"✅ {len(rows_normalizados)} registros guardados")
    
    # Mostrar una muestra de lo que se guardó
    print("\n📋 Muestra de datos guardados (primeros 3 registros):")
    cursor.execute("""
        SELECT arti_nombre, dept_nombre, promedio_kg, enma_fecha 
        FROM dane_normalizado 
        LIMIT 3
    """)
    for row in cursor.fetchall():
        print(f"   Artículo: {row[0]}, Depto: {row[1]}, Precio: {row[2]}, Fecha: {row[3]}")
    
else:
    print("❌ No hay datos válidos para insertar")
    print("\n🔧 Sugerencia: Revisa la estructura real de los datos en la inspección inicial")

# =========================
# ÍNDICES
# =========================

if rows_normalizados:
    print("\n📊 Creando índices...")
    try:
        cursor.execute("CREATE INDEX idx_arti_nombre ON dane_normalizado(arti_nombre)")
        cursor.execute("CREATE INDEX idx_enma_fecha ON dane_normalizado(enma_fecha)")
        cursor.execute("CREATE INDEX idx_grup_nombre ON dane_normalizado(grup_nombre)")
        conn.commit()
        print("✅ Índices creados")
    except Exception as e:
        print(f"⚠️ Error creando índices: {e}")

# =========================
# CLOSE
# =========================

cursor.close()
conn.close()

print("\n🎉 ETL FINALIZADO")