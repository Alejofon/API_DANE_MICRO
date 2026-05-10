import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from services.clima_service import get_climate_data
from services.soil_service import get_soil_data
from services.inputs_service import get_inputs_index
import requests
from flask import jsonify, request


# -----------------------------------
# CONFIG FLASK
# -----------------------------------

app = Flask(__name__)
CORS(app)

# -----------------------------------
# DATABASE CONNECTION
# -----------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Retorna una conexión a PostgreSQL con cursor de diccionario"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# -----------------------------------
# HOME
# -----------------------------------

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "API MISIEMBRA -  DATOAS AGRICOLAS DE COLOMBIA",
        "endpoints": {
            
        }
    })

# -----------------------------------
# LISTAR PRODUCTOS (con filtros)
# -----------------------------------

@app.route("/productos")
def listar_productos():
    """
    Lista productos con filtros opcionales:
    - grupo: filtrar por grupo (FRUTAS, VERDURAS, etc)
    - departamento: filtrar por departamento
    - precio_min: precio promedio mínimo
    - precio_max: precio promedio máximo
    - fecha_inicio y fecha_fin: rango de fechas
    - limit: cantidad de resultados (default 100)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener parámetros de consulta
        grupo = request.args.get('grupo')
        departamento = request.args.get('departamento')
        precio_min = request.args.get('precio_min')
        precio_max = request.args.get('precio_max')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        limit = request.args.get('limit', 100, type=int)
        
        # Construir consulta dinámica
        query = """
            SELECT DISTINCT 
                arti_nombre as producto,
                grup_nombre as grupo,
                dept_nombre as departamento,
                MIN(promedio_kg) as precio_minimo_historico,
                MAX(promedio_kg) as precio_maximo_historico,
                AVG(promedio_kg) as precio_promedio_historico,
                COUNT(*) as total_registros
            FROM dane_normalizado
            WHERE 1=1
        """
        params = []
        
        if grupo:
            query += " AND grup_nombre ILIKE %s"
            params.append(f"%{grupo}%")
        
        if departamento:
            query += " AND dept_nombre ILIKE %s"
            params.append(f"%{departamento}%")
        
        if precio_min:
            query += " AND promedio_kg >= %s"
            params.append(float(precio_min))
        
        if precio_max:
            query += " AND promedio_kg <= %s"
            params.append(float(precio_max))
        
        if fecha_inicio:
            query += " AND enma_fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += " AND enma_fecha <= %s"
            params.append(fecha_fin)
        
        query += " GROUP BY arti_nombre, grup_nombre, dept_nombre ORDER BY arti_nombre LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "total": len(results),
            "filtros_aplicados": {
                "grupo": grupo,
                "departamento": departamento,
                "precio_min": precio_min,
                "precio_max": precio_max,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            },
            "data": results
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------------
# BUSCAR PRODUCTO ESPECÍFICO
# -----------------------------------


@app.route("/grupos")
def listar_grupos():
    """Lista todos los grupos de productos (FRUTAS, VERDURAS, etc)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                grup_nombre as grupo,
                COUNT(DISTINCT arti_nombre) as total_productos,
                COUNT(*) as total_registros,
                AVG(promedio_kg)::NUMERIC(10,2) as precio_promedio_general
            FROM dane_normalizado
            WHERE grup_nombre IS NOT NULL
            GROUP BY grup_nombre
            ORDER BY grup_nombre
        """)
        
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "total": len(results),
            "data": results
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------------
# ESTADÍSTICAS GENERALES
# -----------------------------------

@app.route("/estadisticas")
def estadisticas_generales():
    """Estadísticas generales de toda la base de datos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_registros,
                COUNT(DISTINCT arti_nombre) as total_productos,
                COUNT(DISTINCT dept_nombre) as total_departamentos,
                COUNT(DISTINCT grup_nombre) as total_grupos,
                MIN(enma_fecha) as fecha_mas_antigua,
                MAX(enma_fecha) as fecha_mas_reciente,
                AVG(promedio_kg)::NUMERIC(10,2) as precio_promedio_general,
                MIN(promedio_kg) as precio_minimo_absoluto,
                MAX(promedio_kg) as precio_maximo_absoluto
            FROM dane_normalizado
        """)
        
        stats = cursor.fetchone()
        
        # Top 5 productos más caros
        cursor.execute("""
            SELECT 
                arti_nombre as producto,
                AVG(promedio_kg)::NUMERIC(10,2) as precio_promedio
            FROM dane_normalizado
            GROUP BY arti_nombre
            ORDER BY precio_promedio DESC
            LIMIT 5
        """)
        
        top_caros = cursor.fetchall()
        
        # Top 5 productos más baratos
        cursor.execute("""
            SELECT 
                arti_nombre as producto,
                AVG(promedio_kg)::NUMERIC(10,2) as precio_promedio
            FROM dane_normalizado
            GROUP BY arti_nombre
            ORDER BY precio_promedio ASC
            LIMIT 5
        """)
        
        top_baratos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "estadisticas_generales": stats,
            "productos_mas_caros": top_caros,
            "productos_mas_baratos": top_baratos
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------------
# CONSULTAR POR FECHA ESPECÍFICA
# -----------------------------------

@app.route("/fecha/<fecha>")
def consultar_por_fecha(fecha):
    """Obtiene todos los precios de una fecha específica"""
    try:
        # Validar formato de fecha
        datetime.strptime(fecha, '%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                arti_nombre as producto,
                grup_nombre as grupo,
                dept_nombre as departamento,
                muni_nombre as municipio,
                promedio_kg as precio_promedio,
                minimo_kg as precio_minimo,
                maximo_kg as precio_maximo,
                fuen_nombre as fuente
            FROM dane_normalizado
            WHERE enma_fecha = %s
            ORDER BY arti_nombre
            LIMIT 1000
        """, (fecha,))
        
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "fecha": fecha,
            "total_registros": len(results),
            "data": results
        })
        
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Formato de fecha inválido. Use YYYY-MM-DD"
        }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
# -----------------------------------
# SOIL DATA
# -----------------------------------

@app.route("/soil")
def soil_data():

    try:

        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        if lat is None or lon is None:
            return jsonify({
                "success": False,
                "error": "Debe enviar lat y lon"
            }), 400

        soil = get_soil_data(lat, lon)

        return jsonify({
            "success": True,
            "coordinates": {
                "lat": lat,
                "lon": lon
            },
            "soil_data": soil
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -----------------------------------
# CLIMATE DATA
# -----------------------------------

@app.route("/climate")
def climate_data():

    try:

        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        if lat is None or lon is None:

            return jsonify({
                "success": False,
                "error": "Debe enviar lat y lon"
            }), 400

        climate = get_climate_data(lat, lon)

        return jsonify({
            "success": True,
            "coordinates": {
                "lat": lat,
                "lon": lon
            },
            "climate_data": climate
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -----------------------------------
# INPUTS DATA
# -----------------------------------

@app.route("/inputs")
def inputs_data():
    try:
        result = get_inputs_index(limit=1)

        if not result:
            return jsonify({
                "success": False,
                "error": "No se pudo obtener información del índice de insumos"
            }), 500

        return jsonify({
            "success": True,
            "source": "datos.gov.co/gwbi-fnzs",
            "context": result["context"],
            "data": result["data"],
            "highlights": result["highlights"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/analisis-terreno")
def analisis_terreno():
    """
    Endpoint unificado para la app móvil.
    Recibe: lat, lon, departamento, municipio.
    Retorna: clima, suelo, índice de insumos y estadísticas de precios DANE
    para los tres grupos de interés.
    """
    try:
        # --- Obtener parámetros ---
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        departamento = request.args.get("departamento", "").strip().upper()
        municipio = request.args.get("municipio", "").strip().upper()

        if lat is None or lon is None or not departamento:
            return jsonify({
                "success": False,
                "error": "Se requieren lat, lon y departamento"
            }), 400

        # ---------------------------------------------------
        # 1. Clima (usa el servicio existente)
        # ---------------------------------------------------
        climate = get_climate_data(lat, lon)
        if climate is None:
            climate = {"error": "No se pudo obtener datos climáticos"}

        # ---------------------------------------------------
        # 2. Suelo (usa el servicio existente)
        # ---------------------------------------------------
        soil = get_soil_data(lat, lon)
        if soil is None:
            soil = {"error": "No se pudo obtener datos de suelo"}

        # ---------------------------------------------------
        # 3. Índice de insumos (usa el servicio existente)
        # ---------------------------------------------------
        inputs_result = get_inputs_index(limit=1)
        if not inputs_result:
            inputs_result = {"error": "No se pudo obtener el índice de insumos"}

        # ---------------------------------------------------
        # 4. Precios DANE específicos del departamento/municipio
        #    y los tres grupos de interés
        # ---------------------------------------------------
        grupos_interes = [
            "FRUTAS",
            "TUBERCULOS, RAICES Y PLATANOS",
            "VERDURAS Y HORTALIZAS"
        ]

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        precios_por_grupo = {}

        for grupo in grupos_interes:
            # Construir consulta para el grupo
            query = """
                WITH productos_stats AS (
                    SELECT 
                        arti_nombre,
                        grup_nombre,
                        AVG(promedio_kg) as precio_promedio,
                        MIN(promedio_kg) as precio_min,
                        MAX(promedio_kg) as precio_max,
                        COUNT(*) as num_registros,
                        MIN(enma_fecha) as fecha_inicio,
                        MAX(enma_fecha) as fecha_fin
                    FROM dane_normalizado
                    WHERE grup_nombre = %s
                      AND dept_nombre ILIKE %s
            """
            params = [grupo, departamento]

            if municipio:
                query += " AND muni_nombre ILIKE %s"
                params.append(municipio)

            query += """
                    GROUP BY arti_nombre, grup_nombre
                )
                SELECT *,
                       RANK() OVER (ORDER BY precio_promedio DESC) as rank_caro,
                       RANK() OVER (ORDER BY precio_promedio ASC) as rank_barato
                FROM productos_stats
                ORDER BY precio_promedio DESC
            """

            cursor.execute(query, params)
            productos = cursor.fetchall()

            # Calcular estadísticas generales para el grupo
            if productos:
                precio_promedio_grupo = sum(p["precio_promedio"] for p in productos) / len(productos)
                producto_mas_caro = productos[0]  # ya ordenado desc
                producto_mas_barato = productos[-1]
                # Top 3 caros y top 3 baratos
                top_caros = productos[:3]
                # Los más baratos (últimos 3, podrían estar en orden inverso)
                productos_asc = sorted(productos, key=lambda x: x["precio_promedio"])
                top_baratos = productos_asc[:3]
            else:
                precio_promedio_grupo = None
                producto_mas_caro = None
                producto_mas_barato = None
                top_caros = []
                top_baratos = []

            precios_por_grupo[grupo] = {
                "estadisticas": {
                    "total_productos": len(productos),
                    "precio_promedio_grupo": round(precio_promedio_grupo, 2) if precio_promedio_grupo is not None else None,
                    "producto_mas_caro": producto_mas_caro["arti_nombre"] if producto_mas_caro else None,
                    "precio_mas_caro": round(producto_mas_caro["precio_promedio"], 2) if producto_mas_caro else None,
                    "producto_mas_barato": producto_mas_barato["arti_nombre"] if producto_mas_barato else None,
                    "precio_mas_barato": round(producto_mas_barato["precio_promedio"], 2) if producto_mas_barato else None,
                    "fecha_inicio_global": productos[0]["fecha_inicio"] if productos else None,
                    "fecha_fin_global": productos[0]["fecha_fin"] if productos else None
                },
                "productos_mas_caros": [
                    {
                        "producto": p["arti_nombre"],
                        "precio_promedio": round(p["precio_promedio"], 2),
                        "unidad": "COP/kg"
                    } for p in top_caros
                ],
                "productos_mas_baratos": [
                    {
                        "producto": p["arti_nombre"],
                        "precio_promedio": round(p["precio_promedio"], 2),
                        "unidad": "COP/kg"
                    } for p in top_baratos
                ]
            }

        cursor.close()
        conn.close()

        # ---------------------------------------------------
        # Construir la respuesta unificada con CONTEXTO
        # ---------------------------------------------------
        respuesta = {
            "success": True,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "endpoint": "/analisis-terreno"
            },
            "location": {
                "lat": lat,
                "lon": lon,
                "departamento": departamento,
                "municipio": municipio if municipio else "No especificado"
            },
            "contexto_general": (
                "Información consolidada para la evaluación de cultivos. "
                "Incluye clima, suelo, índice de precios de insumos (nacional) y "
                "precios de mercado del DANE para los tres principales grupos de alimentos "
                "en el departamento/municipio indicado. Los precios están en COP/kg."
            ),
            "clima": {
                "context": (
                    "Datos actuales y pronóstico diario de variables meteorológicas relevantes "
                    "para la agricultura: temperatura, humedad relativa, precipitación, viento "
                    "y evapotranspiración de referencia (ET₀). Fuente: Open-Meteo (open-meteo.com). "
                    "Unidades: °C, %, mm, km/h."
                ),
                "data": climate
            },
            "suelo": {
                "context": (
                    "Propiedades del suelo superficial (0-5 cm) según ISRIC SoilGrids vía WCS. "
                    "Los valores representan pH en H₂O, contenido de arcilla (%) y arena (%). "
                    "Valores nulos indican datos no disponibles o máscara (por ej., cuerpos de agua)."
                ),
                "data": soil
            },
            "insumos": {
                "context": inputs_result.get("context", {}),
                "data": inputs_result.get("highlights", inputs_result.get("data", {}))
            },
            "precios_mercado": {
                "context": (
                    "Precios de venta minorista recolectados por el DANE en centrales mayoristas. "
                    "Se presentan estadísticas por grupo de producto para el departamento/municipio seleccionado. "
                    "Los valores (COP/kg) son promedios históricos en el rango de fechas disponible. "
                    "Esta información ayuda al modelo a evaluar la rentabilidad potencial de los cultivos."
                ),
                "por_grupo": precios_por_grupo
            }
        }

        return jsonify(respuesta)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -----------------------------------
# BUSCAR INSUMOS AGRÍCOLAS CERCANOS (GOOGLE PLACES)
# -----------------------------------   


GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
# -----------------------------------
# FUNCIONES INTERNAS DE BÚSQUEDA (CORREGIDAS)
# -----------------------------------

KEYWORDS_AGRO = [
    "agro", "semilla", "fertilizante", "insumo", "agricola", "agropecuaria", 
    "veterinaria", "finca", "campo", "abono", "pasto", "ganado", "cultivo", 
    "riego", "cosecha", "concentrado", "bulto"
]

def _es_negocio_valido(lugar):
    """Revisa el nombre y también las categorías de Google para no borrar locales reales"""
    nombre = lugar.get("displayName", {}).get("text", "").lower()
    # Revisamos también los 'types' que devuelve Google (ej: 'hardware_store')
    tipos = lugar.get("types", [])
    
    # Si el nombre tiene algo de agro, es válido
    if any(kw in nombre for kw in KEYWORDS_AGRO):
        return True
    
    # Si Google lo categoriza como algo útil en el campo, también
    categorias_utiles = ["hardware_store", "farm", "garden_center"]
    if any(t in categorias_utiles for t in tipos):
        return True
        
    return False

def _buscar_con_texto(lat, lon, radius, estricto=False):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        # IMPORTANTE: Agregamos 'places.types' para que el filtro funcione mejor
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.googleMapsUri,places.types"
    }
    
    payload = {
        "textQuery": "agropecuaria insumos agricolas",
        "languageCode": "es",
        "maxResultCount": 20
    }

    # Si es búsqueda en el pueblo (estricto), usamos Restriction. 
    # Si es regional, usamos Bias para que Google no se bloquee.
    if estricto:
        payload["locationRestriction"] = {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": float(radius)
            }
        }
        # Solo podemos usar DISTANCE si hay una restricción activa
        payload["rankPreference"] = "DISTANCE"
    else:
        payload["locationBias"] = {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": float(radius)
            }
        }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        lugares = r.json().get("places", [])
        
        # Aplicamos el filtro de palabras agro
        filtrados = [l for l in lugares if _es_negocio_valido(l)]
        return filtrados
    except Exception as e:
        print(f"Error en búsqueda: {e}")
        return []

def buscar_proveedores_cercanos(lat, lon):
    # INTENTO 1: Turmequé (Radio de 5km, obligatorio estar cerca)
    lugares = _buscar_con_texto(lat, lon, 5000, estricto=True)
    
    # INTENTO 2: Si Turmequé falla por GPS, buscamos a 15km (municipios vecinos como Ventaquemada/Nuevo Colón)
    if not lugares:
        lugares = _buscar_con_texto(lat, lon, 15000, estricto=False)
        
    # INTENTO 3: Regional (50km)
    if not lugares:
        lugares = _buscar_con_texto(lat, lon, 50000, estricto=False)

    if not lugares:
        return {
            "success": True,
            "total": 0,
            "data": [],
            "mensaje": "No se encontraron locales agropecuarios. Intente con otra ubicación."
        }

    proveedores = []
    for lugar in lugares[:8]: # Mostramos hasta 8 para dar opciones
        proveedores.append({
            "nombre": lugar.get("displayName", {}).get("text", "Sin nombre"),
            "direccion": lugar.get("formattedAddress", "Dirección no disponible"),
            "maps_link": lugar.get("googleMapsUri", "")
        })

    return {"success": True, "total": len(proveedores), "data": proveedores}

def _buscar_nearby(lat, lon, radius, included_types):
    """Búsqueda cercana (v1): Usa tipos oficiales de Google"""
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.googleMapsUri"
    }
    
    # OJO: searchNearby tiene un límite máximo de 50000 (50km). 
    # Si le pasas 100000, Google dará error.
    radio_ajustado = min(float(radius), 50000.0)

    payload = {
        "includedTypes": included_types,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": radio_ajustado
            }
        },
        "languageCode": "es"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json().get("places", [])
    except Exception as e:
        print(f"Error en búsqueda nearby: {e}")
        return []



@app.route("/buscar-insumos")
def buscar_insumos():
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is None or lon is None:
            return jsonify({"success": False, "error": "Faltan coordenadas"}), 400
        resultado = buscar_proveedores_cercanos(lat, lon)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------------
# START APP
# -----------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)