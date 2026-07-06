import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from services.clima_service import get_climate_data, get_elevation
from services.soil_service import get_soil_data
from services.inputs_service import get_inputs_index
from services.agro_technical_service import (
    obtener_parametros_tecnicos,
    obtener_candidatos_cultivo,
    resolver_parametros_tecnicos,
)
from services.validacion_service import completar_parametros
from services.calculo_agricola import calcular_plan, formatear_resultados_para_ui, construir_candidatos_respaldo
from services.utils_numeros import parsear_numero, area_a_m2
from services.redaccion_service import redactar_plan_final, plan_no_apto
from services.tabla_referencia_cultivos import (
    buscar_en_tabla,
    es_apto_por_altitud,
    es_apto_por_temperatura,
    candidatos_por_altitud,
)
from services.cache_tecnico_service import (
    asegurar_tabla as asegurar_tabla_cache,
    obtener_candidatos as obtener_candidatos_cache,
    guardar_candidatos as guardar_candidatos_cache,
)
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

# Crea la tabla de cache de parámetros técnicos si no existe (idempotente).
# Se hace al importar el módulo para que el primer request ya la tenga lista.
try:
    asegurar_tabla_cache()
except Exception as _e:
    print(f"[startup] No se pudo asegurar la tabla de cache: {_e}")

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
# OPCIONES DE CULTIVO (candidatos con datos reales + filtro de viabilidad)
# -----------------------------------

@app.route("/opciones-cultivo", methods=["POST"])
def opciones_cultivo():
    """
    Reemplaza la llamada directa Flutter -> OpenAI de OptionsPage.

    La IA es la GENERADORA DE IDEAS (ahí está el valor: propone cultivos
    novedosos/de nicho apropiados al clima Y a la relación presupuesto↔terreno,
    no solo lo obvio que el agricultor ya conoce). La tabla curada NO limita
    las ideas: solo aporta NÚMEROS confiables cuando un cultivo propuesto está
    en ella. Flujo:
      1. Genera candidatos con la IA (consciente de presupuesto/área para
         proponer sistemas intensivos vs extensivos según el perfil). El set
         se cachea por zona+intensidad, así que la 2da vez es instantáneo.
      2. Para cada candidato: si está en la tabla curada, se usan SUS cifras
         (confiables); si no, las que trajo la IA. Se completan huecos con
         completar_parametros.
      3. Calcula la rentabilidad real de cada uno con calculo_agricola.py.
      4. Devuelve los 5 mejores por ganancia estimada.

    Si la IA falla del todo (sin API key, timeout, red), cae a la tabla curada
    filtrada por clima; y si ni eso, a un respaldo genérico. La app SIEMPRE
    devuelve algo.
    """
    try:
        body = request.get_json(force=True, silent=True) or {}

        departamento = str(body.get("departamento", "")).strip()
        municipio = str(body.get("municipio", "")).strip()
        presupuesto_raw = body.get("presupuesto")
        area_raw = body.get("area")
        unidad = str(body.get("unidad", "Metros cuadrados"))
        tipo_terreno = body.get("tipo_terreno")
        datos_analisis = body.get("datos_analisis")

        if not departamento or not municipio:
            return jsonify({"success": False, "error": "Se requieren departamento y municipio"}), 400

        presupuesto_cop = parsear_numero(presupuesto_raw)
        area_disponible_m2 = area_a_m2(area_raw, unidad)

        if presupuesto_cop <= 0 or area_disponible_m2 <= 0:
            return jsonify({"success": False, "error": "presupuesto y area deben ser mayores a 0"}), 400

        contexto_clima_suelo = _formatear_contexto_clima_suelo(datos_analisis)

        lat = body.get("lat")
        lon = body.get("lon")
        altitud = get_elevation(lat, lon) if (lat is not None and lon is not None) else None
        temperatura = _temperatura_de_analisis(datos_analisis)

        usando_respaldo_total = False
        error_busqueda = None

        # ---------------------------------------------------------
        # 1. IDEAS: cache de candidatos IA por zona+intensidad; si no hay,
        #    se le piden a la IA (consciente de presupuesto/terreno). La IA
        #    es la fuente de novedad; el cache evita repetir el costo/espera.
        # ---------------------------------------------------------
        bracket = _bracket_intensidad(presupuesto_cop, area_disponible_m2)
        candidatos_crudos = obtener_candidatos_cache(departamento, municipio, bracket)
        origen_candidatos = "cache_ia" if candidatos_crudos else None

        if not candidatos_crudos:
            resultado_busqueda = obtener_candidatos_cultivo(
                departamento, municipio, contexto_clima_suelo, tipo_terreno,
                presupuesto_cop=presupuesto_cop, area_m2=area_disponible_m2,
            )
            candidatos_crudos = resultado_busqueda.get("candidatos", []) if isinstance(resultado_busqueda, dict) else []
            error_busqueda = resultado_busqueda.get("error") if isinstance(resultado_busqueda, dict) else None
            if candidatos_crudos:
                origen_candidatos = "ia_busqueda"
                try:
                    guardar_candidatos_cache(departamento, municipio, bracket, candidatos_crudos)
                except Exception as _e:
                    print(f"[opciones-cultivo] No se pudo cachear candidatos: {_e}")

        # Armar la lista (nombre, parametros). Si el candidato está en la
        # tabla curada, se usan SUS números (confiables) en vez de los de la IA.
        pares = []  # (nombre, parametros_crudos, fuente_numeros)
        for candidato in candidatos_crudos:
            nombre = str(candidato.get("nombre_cultivo", "")).strip()
            if not nombre:
                continue
            en_tabla = buscar_en_tabla(nombre)
            if en_tabla:
                pares.append((nombre, en_tabla, "tabla_curada"))
            else:
                pares.append((nombre, candidato, "ia_busqueda"))

        # ---------------------------------------------------------
        # 2. Fallback si la IA no dio nada: tabla curada filtrada por clima.
        # ---------------------------------------------------------
        if not pares:
            candidatos_tabla = candidatos_por_altitud(altitud, temperatura)
            if candidatos_tabla:
                origen_candidatos = "fallback_tabla_curada"
                for nombre, params in candidatos_tabla:
                    pares.append((nombre, params, "tabla_curada"))

        # 3. Último recurso: respaldo genérico (la app nunca se queda vacía).
        if not pares:
            usando_respaldo_total = True
            origen_candidatos = "respaldo_generico"
            print(f"[opciones-cultivo] FALLBACK TOTAL para {municipio}, {departamento}. Motivo: {error_busqueda}")
            for nombre, params in construir_candidatos_respaldo():
                pares.append((nombre, params, "respaldo_generico"))

        evaluados = []
        for nombre, parametros_crudos, fuente_numeros in pares:
            parametros_completos, campos_estimados = completar_parametros(parametros_crudos)
            if usando_respaldo_total:
                campos_estimados = ["todos (respaldo genérico, búsqueda no disponible)"]

            precio_dane = _buscar_precio_dane_para_cultivo(nombre, departamento, municipio)
            calculado = calcular_plan(
                parametros_completos, presupuesto_cop, area_disponible_m2, precio_dane_kg=precio_dane
            )
            evaluados.append((nombre, calculado, campos_estimados))

        # Si hay nombres repetidos (la IA a veces sugiere variantes del
        # mismo cultivo), nos quedamos con la de mejor ganancia.
        mejores_por_nombre = {}
        for nombre, calculado, campos_estimados in evaluados:
            clave = nombre.strip().lower()
            actual = mejores_por_nombre.get(clave)
            if actual is None or calculado["ganancia_estimada_cop"] > actual[1]["ganancia_estimada_cop"]:
                mejores_por_nombre[clave] = (nombre, calculado, campos_estimados)

        evaluados_unicos = list(mejores_por_nombre.values())

        # FILTRO DE VIABILIDAD: la pantalla de opciones SOLO muestra proyectos
        # rentables. Un proyecto es viable si no está marcado "No viable" y su
        # ganancia estimada es positiva. Nunca se le propone al agricultor algo
        # que no puede hacer o que da pérdida.
        viables = [
            (nombre, calc, campos_est)
            for nombre, calc, campos_est in evaluados_unicos
            if calc["nivel_rentabilidad"] != "No viable" and calc["ganancia_estimada_cop"] > 0
        ]
        viables.sort(key=lambda item: item[1]["ganancia_estimada_cop"], reverse=True)
        top = viables[:5]

        # Si NINGÚN cultivo es viable con este presupuesto/área, no se inventa
        # un proyecto: se devuelve un mensaje honesto con el requisito mínimo
        # más cercano (el candidato que menos lejos quedó de ser rentable).
        if not top:
            no_viables = sorted(
                evaluados_unicos,
                key=lambda item: item[1].get("presupuesto_minimo_recomendado_cop") or float("inf"),
            )
            sugerencia = None
            if no_viables:
                nombre_cercano, calc_cercano, _ = no_viables[0]
                sugerencia = {
                    "cultivo_mas_cercano": nombre_cercano,
                    "motivo": calc_cercano.get("motivo_no_viable"),
                    "area_minima_rentable_m2": round((calc_cercano.get("area_minima_rentable_ha") or 0) * 10000),
                    "presupuesto_minimo_cop": calc_cercano.get("presupuesto_minimo_recomendado_cop"),
                }
            return jsonify({
                "opciones": [],
                "sin_opciones_viables": True,
                "mensaje": (
                    "Con el presupuesto y el área indicados no encontramos un cultivo "
                    "rentable en esta zona. Ajusta el presupuesto o el área e intenta de nuevo."
                ),
                "sugerencia_minimo": sugerencia,
                "_debug_calculo": {
                    "zona_consultada": f"{municipio}, {departamento}",
                    "origen_candidatos": origen_candidatos,
                    "bracket_intensidad": bracket,
                    "altitud_msnm": altitud,
                    "evaluados": len(evaluados_unicos),
                    "error_busqueda": error_busqueda,
                },
            })

        return jsonify({
            "opciones": [nombre for nombre, _, _ in top],
            "_debug_calculo": {
                "zona_consultada": f"{municipio}, {departamento}",
                "origen_candidatos": origen_candidatos,
                "bracket_intensidad": bracket,
                "altitud_msnm": altitud,
                "usando_respaldo_total": usando_respaldo_total,
                "error_busqueda": error_busqueda,
                "candidatos": [
                    {
                        "cultivo": nombre,
                        "nivel_rentabilidad": calc["nivel_rentabilidad"],
                        "ganancia_estimada_cop": calc["ganancia_estimada_cop"],
                        "area_recomendada_ha": calc["area_recomendada_ha"],
                        "area_recomendada_m2": calc["area_recomendada_m2"],
                        "campos_estimados": campos_est,
                        "ganancia_atipica": calc.get("ganancia_atipica", False),
                    }
                    for nombre, calc, campos_est in top
                ],
            },
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -----------------------------------
# PLAN DE CULTIVO (cálculo real en backend + redacción final por IA)
# -----------------------------------

def _formatear_contexto_clima_suelo(datos_analisis):
    """
    Convierte el bloque 'datos_analisis' (la misma respuesta de
    /analisis-terreno que ya recibe Flutter) en texto plano para
    dárselo de contexto a la IA de búsqueda técnica.
    """
    if not datos_analisis:
        return None

    partes = []
    clima = (datos_analisis.get("clima") or {}).get("data")
    if clima:
        partes.append(
            f"Clima: temp {clima.get('current', {}).get('temperature')}°C, "
            f"humedad {clima.get('current', {}).get('humidity')}%, "
            f"precipitación {clima.get('daily', {}).get('precipitation_sum')}mm"
        )

    suelo = (datos_analisis.get("suelo") or {}).get("data")
    if suelo:
        partes.append(
            f"Suelo (0-5cm): pH {suelo.get('ph')}, arcilla {suelo.get('clay')}%, arena {suelo.get('sand')}%"
        )

    return "\n".join(partes) if partes else None


def _bracket_intensidad(presupuesto_cop, area_m2):
    """
    Clasifica la relación presupuesto↔terreno en un 'bracket' de intensidad
    ($/m²) para (a) darle contexto a la IA y (b) cachear los candidatos por
    perfil: dos usuarios con la misma zona y perfil de inversión reciben el
    mismo set de ideas sin volver a gastar una llamada de IA.
    """
    try:
        inversion_por_m2 = float(presupuesto_cop) / float(area_m2) if area_m2 else 0
    except (TypeError, ValueError, ZeroDivisionError):
        inversion_por_m2 = 0
    # Cultivos de campo abierto en Colombia cuestan ~$200-2200/m² todo incluido.
    # Tener bastante más que eso disponible por m² => hay margen para
    # intensificar (hidroponía, invernadero, alto valor). Tener mucho menos =>
    # el fuerte es el área, conviene extensivo de bajo insumo.
    if inversion_por_m2 >= 5000:
        return "intensivo"      # poca área, buen presupuesto
    if inversion_por_m2 <= 500:
        return "extensivo"      # mucha área, presupuesto ajustado
    return "mixto"


def _temperatura_de_analisis(datos_analisis):
    """
    Temperatura media (°C) del bloque datos_analisis, para verificar aptitud
    climática cuando no se dispone de altitud. Retorna float o None.
    Usa el promedio de max/min diarios si están; si no, la temperatura actual.
    """
    if not datos_analisis:
        return None
    clima = (datos_analisis.get("clima") or {}).get("data") or {}
    daily = clima.get("daily") or {}
    tmax = daily.get("temperature_max")
    tmin = daily.get("temperature_min")
    try:
        if tmax is not None and tmin is not None:
            return (float(tmax) + float(tmin)) / 2.0
    except (TypeError, ValueError):
        pass
    actual = (clima.get("current") or {}).get("temperature")
    try:
        return float(actual) if actual is not None else None
    except (TypeError, ValueError):
        return None


# SIPSA/DANE solo reporta precios en las ~20 ciudades con central mayorista
# propia (Corabastos-Bogotá, Medellín, Cali, etc.) — el nombre que aparece en
# dept_nombre es el departamento de ESA central, no el departamento de la
# finca. Departamentos sin central propia (ej. Cundinamarca: Villapinzón,
# Chocontá, Tocancipá) nunca calzan por nombre exacto y antes caían directo
# a precio nacional. Este mapa los conecta con la central mayorista real más
# cercana (aproximación geográfica documentada, no un dato oficial en sí)
# ANTES de rendirse al promedio nacional.
DEPARTAMENTO_A_MERCADO_DANE = {
    "AMAZONAS": None,
    "ANTIOQUIA": "ANTIOQUIA",
    "ARAUCA": "META",
    "ATLANTICO": "ATLÁNTICO",
    "ATLÁNTICO": "ATLÁNTICO",
    "BOGOTA": "BOGOT",
    "BOGOTÁ": "BOGOT",
    "BOGOTA, D.C.": "BOGOT",
    "BOGOTÁ, D.C.": "BOGOT",
    "BOLIVAR": "BOLÍVAR",
    "BOLÍVAR": "BOLÍVAR",
    "BOYACA": "BOYACÁ",
    "BOYACÁ": "BOYACÁ",
    "CALDAS": "CALDAS",
    "CAQUETA": "HUILA",
    "CAQUETÁ": "HUILA",
    "CASANARE": "META",
    "CAUCA": "CAUCA",
    "CESAR": "CESAR",
    "CHOCO": "ANTIOQUIA",
    "CHOCÓ": "ANTIOQUIA",
    "CORDOBA": "CÓRDOBA",
    "CÓRDOBA": "CÓRDOBA",
    "CUNDINAMARCA": "BOGOT",
    "GUAINIA": None,
    "GUAINÍA": None,
    "GUAVIARE": "META",
    "HUILA": "HUILA",
    "LA GUAJIRA": "MAGDALENA",
    "GUAJIRA": "MAGDALENA",
    "MAGDALENA": "MAGDALENA",
    "META": "META",
    "NARINO": "NARIÑO",
    "NARIÑO": "NARIÑO",
    "NORTE DE SANTANDER": "NORTE DE SANTANDER",
    "PUTUMAYO": "NARIÑO",
    "QUINDIO": "QUINDÍO",
    "QUINDÍO": "QUINDÍO",
    "RISARALDA": "RISARALDA",
    "SAN ANDRES Y PROVIDENCIA": None,
    "SAN ANDRÉS Y PROVIDENCIA": None,
    "SANTANDER": "SANTANDER",
    "SUCRE": "SUCRE",
    "TOLIMA": "TOLIMA",
    "VALLE DEL CAUCA": "VALLE DEL CAUCA",
    "VAUPES": None,
    "VAUPÉS": None,
    "VICHADA": "META",
}


def _buscar_precio_dane_para_cultivo(cultivo, departamento=None, municipio=None):
    """
    Consulta DIRECTAMENTE la tabla dane_normalizado (SIPSA/DANE, actualizada
    a diario por el ETL) por el precio promedio real del cultivo pedido.

    Antes esta función solo comparaba contra los top-3 más caros/baratos que
    ya traía /analisis-terreno por grupo de producto — si el cultivo no
    quedaba entre esos 6, el precio real del DANE (que sí existía en la
    tabla) nunca se usaba y el cálculo caía en el precio inventado por la IA.

    Cascada geográfica: municipio -> departamento exacto -> mercado mayorista
    de referencia más cercano (DEPARTAMENTO_A_MERCADO_DANE) -> nacional
    (mejor un precio nacional real que uno alucinado). Se limita a los
    últimos 18 meses para no usar precios desactualizados.
    Retorna el precio promedio (float) o None si no hay ningún dato.
    """
    cultivo_norm = (cultivo or "").strip()
    if not cultivo_norm:
        return None

    terminos_nombre = [f"%{cultivo_norm}%"]
    primera_palabra = cultivo_norm.split()[0]
    if primera_palabra.lower() != cultivo_norm.lower():
        terminos_nombre.append(f"%{primera_palabra}%")

    niveles_geo = []
    if municipio:
        niveles_geo.append(("muni_nombre", municipio))
    if departamento:
        niveles_geo.append(("dept_nombre", departamento))
        mercado_referencia = DEPARTAMENTO_A_MERCADO_DANE.get(departamento.strip().upper())
        if mercado_referencia and mercado_referencia.upper() != departamento.strip().upper():
            niveles_geo.append(("dept_nombre", mercado_referencia))
    niveles_geo.append((None, None))  # nacional, sin filtro geográfico

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        for columna_geo, valor_geo in niveles_geo:
            for termino in terminos_nombre:
                query = """
                    SELECT AVG(promedio_kg) AS precio_promedio, COUNT(*) AS num_registros
                    FROM dane_normalizado
                    WHERE arti_nombre ILIKE %s
                      AND enma_fecha >= (CURRENT_DATE - INTERVAL '18 months')
                """
                params = [termino]
                if columna_geo:
                    query += f" AND {columna_geo} ILIKE %s"
                    params.append(f"%{valor_geo}%")

                cursor.execute(query, params)
                fila = cursor.fetchone()
                if fila and fila["num_registros"] and fila["precio_promedio"]:
                    cursor.close()
                    conn.close()
                    return float(fila["precio_promedio"])

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[_buscar_precio_dane_para_cultivo] Error consultando dane_normalizado: {e}")

    return None


@app.route("/plan-cultivo", methods=["POST"])
def plan_cultivo():
    """
    Endpoint que reemplaza la llamada directa Flutter -> OpenAI para el
    plan detallado de un cultivo. Flujo:
      1. Pide parámetros técnicos crudos a una IA con búsqueda web
         restringida a fuentes agrícolas confiables.
      2. Valida esos parámetros (rechaza cifras absurdas), reintenta
         una vez si es necesario, y si sigue fallando usa un fallback
         genérico conservador por categoría de cultivo.
      3. Calcula TODO en Python (calculo_agricola.py): plantas/ha,
         costos, área financiable, área recomendada, producción,
         ingresos, ganancia, rentabilidad.
      4. Le pide a gpt-4.1-mini que SOLO redacte el texto final,
         reutilizando esas cifras (y el backend las sobrescribe de
         todas formas, por seguridad).

    Devuelve exactamente el mismo esquema JSON que hoy arma
    project_detail_prompt.dart, para que el resto de project_detail_page.dart
    (parsing, UI, guardado en historial) no necesite cambios.
    """
    try:
        body = request.get_json(force=True, silent=True) or {}

        cultivo = str(body.get("cultivo", "")).strip()
        departamento = str(body.get("departamento", "")).strip()
        municipio = str(body.get("municipio", "")).strip()
        presupuesto_raw = body.get("presupuesto")
        area_raw = body.get("area")
        unidad = str(body.get("unidad", "Metros cuadrados"))
        tipo_terreno = body.get("tipo_terreno")
        datos_analisis = body.get("datos_analisis")

        if not cultivo or not departamento or not municipio:
            return jsonify({"success": False, "error": "Se requieren cultivo, departamento y municipio"}), 400

        presupuesto_cop = parsear_numero(presupuesto_raw)
        area_disponible_m2 = area_a_m2(area_raw, unidad)

        if presupuesto_cop <= 0 or area_disponible_m2 <= 0:
            return jsonify({"success": False, "error": "presupuesto y area deben ser mayores a 0"}), 400

        contexto_clima_suelo = _formatear_contexto_clima_suelo(datos_analisis)

        # ---------------------------------------------------------
        # 0. Aptitud climática con ALTITUD REAL (Open-Meteo), sin IA.
        #    Si el cultivo está en la tabla curada y su rango de altitud no
        #    cuadra con la elevación real de la zona, se corta aquí mismo
        #    (ej. "Cacao" a 2600 msnm) sin gastar una llamada de IA.
        # ---------------------------------------------------------
        lat = body.get("lat")
        lon = body.get("lon")
        en_tabla = buscar_en_tabla(cultivo)
        if en_tabla:
            altitud = get_elevation(lat, lon) if (lat is not None and lon is not None) else None
            if altitud is not None:
                apto, motivo_alt = es_apto_por_altitud(en_tabla, altitud)
            else:
                apto, motivo_alt = es_apto_por_temperatura(en_tabla, _temperatura_de_analisis(datos_analisis))
            if apto is False:
                plan_final = plan_no_apto(cultivo, motivo_alt, municipio, departamento)
                plan_final["_debug_calculo"] = {
                    "zona_consultada": f"{municipio}, {departamento}",
                    "apto_para_la_zona": False,
                    "motivo_aptitud": motivo_alt,
                    "altitud_msnm": altitud,
                    "origen_parametros": "tabla_curada",
                }
                return jsonify(plan_final)

        # ---------------------------------------------------------
        # 1-2. Parámetros técnicos: tabla curada -> cache -> IA de búsqueda.
        #      Solo se llama a la IA si el cultivo no está curado ni cacheado.
        # ---------------------------------------------------------
        parametros_crudos, origen_parametros = resolver_parametros_tecnicos(
            cultivo, departamento, municipio, contexto_clima_suelo
        )
        error_busqueda = parametros_crudos.get("error") if isinstance(parametros_crudos, dict) else "respuesta no era un dict"
        if error_busqueda:
            print(f"[plan-cultivo] Sin datos usables para '{cultivo}' en {municipio}, {departamento} (origen={origen_parametros}). Motivo: {error_busqueda}")

        # Corte temprano: si la IA determinó que el cultivo NO es apto para
        # el clima/suelo de la zona, no tiene sentido calcular costos ni
        # rendimientos de algo que no debería sembrarse ahí (el caso
        # "mango en el Ártico"). Se responde de inmediato con "No viable" y
        # el motivo real, sin gastar la llamada de redacción.
        if (
            error_busqueda is None
            and isinstance(parametros_crudos, dict)
            and parametros_crudos.get("apto_para_la_zona") is False
        ):
            plan_final = plan_no_apto(
                cultivo, parametros_crudos.get("motivo_aptitud"), municipio, departamento
            )
            plan_final["_debug_calculo"] = {
                "zona_consultada": f"{municipio}, {departamento}",
                "apto_para_la_zona": False,
                "motivo_aptitud": parametros_crudos.get("motivo_aptitud"),
                "origen_parametros": origen_parametros,
            }
            return jsonify(plan_final)

        parametros, campos_estimados = completar_parametros(parametros_crudos)
        advertencia_datos = len(campos_estimados) > 0

        # ---------------------------------------------------------
        # 3. Cálculo real en Python
        # ---------------------------------------------------------
        precio_dane = _buscar_precio_dane_para_cultivo(cultivo, departamento, municipio)
        calculado = calcular_plan(parametros, presupuesto_cop, area_disponible_m2, precio_dane_kg=precio_dane)
        ui = formatear_resultados_para_ui(calculado, parametros)

        # ---------------------------------------------------------
        # 4. Redacción final (solo texto, cifras ya fijas)
        # ---------------------------------------------------------
        ubicacion_texto = f"{municipio}, {departamento}" + (f" - Terreno: {tipo_terreno}" if tipo_terreno else "")
        plan_final = redactar_plan_final(
            cultivo=cultivo,
            ubicacion=ubicacion_texto,
            ui=ui,
            calculado=calculado,
            parametros=parametros,
            advertencia=advertencia_datos,
            ganancia_atipica=calculado.get("ganancia_atipica", False),
        )

        # Metadata útil para depuración / trazabilidad (Flutter puede ignorarla).
        plan_final["_debug_calculo"] = {
            "zona_consultada": f"{municipio}, {departamento}",
            "origen_parametros": origen_parametros,
            "advertencia_datos_genericos": advertencia_datos,
            "error_busqueda": error_busqueda,
            "campos_estimados": campos_estimados,
            "fuentes_consultadas": parametros.get("fuentes_consultadas", []),
            "costo_total_establecimiento_ha": calculado["costo_total_establecimiento_ha"],
            "area_disponible_ha": calculado["area_disponible_ha"],
            "area_recomendada_ha": calculado["area_recomendada_ha"],
            "motivo_no_viable": calculado.get("motivo_no_viable"),
            "ganancia_atipica": calculado.get("ganancia_atipica", False),
            "presupuesto_minimo_recomendado_cop": calculado.get("presupuesto_minimo_recomendado_cop"),
        }

        return jsonify(plan_final)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -----------------------------------
# CÁLCULO DIRECTO (para la app de PRUEBAS / validación de efectividad)
# -----------------------------------

@app.route("/calculo-directo", methods=["POST"])
def calculo_directo():
    """
    Endpoint de VALIDACIÓN. Recibe un cultivo ESPECÍFICO + presupuesto + área
    (+ ubicación) y devuelve la rentabilidad calculada con EXACTAMENTE la misma
    lógica que usa /plan-cultivo (resolver_parametros_tecnicos -> tabla curada /
    cache / IA, completar_parametros, precio DANE real, calcular_plan), pero
    SIN la redacción de texto por IA (más rápido y barato, ideal para hacer
    encuestas en campo comparando contra agricultores experimentados).

    A diferencia de /plan-cultivo, NO rechaza por aptitud climática: para la
    validación el agricultor ya cultiva ese producto, así que se calcula igual
    y la aptitud se reporta solo como dato informativo. Devuelve los números
    crudos y los parámetros técnicos usados, para poder contrastar cada cifra.
    """
    try:
        body = request.get_json(force=True, silent=True) or {}

        cultivo = str(body.get("cultivo", "")).strip()
        departamento = str(body.get("departamento", "")).strip()
        municipio = str(body.get("municipio", "")).strip()
        presupuesto_raw = body.get("presupuesto")
        area_raw = body.get("area")
        unidad = str(body.get("unidad", "Metros cuadrados"))
        tipo_terreno = body.get("tipo_terreno")
        datos_analisis = body.get("datos_analisis")

        if not cultivo or not departamento or not municipio:
            return jsonify({"success": False, "error": "Se requieren cultivo, departamento y municipio"}), 400

        presupuesto_cop = parsear_numero(presupuesto_raw)
        area_disponible_m2 = area_a_m2(area_raw, unidad)

        if presupuesto_cop <= 0 or area_disponible_m2 <= 0:
            return jsonify({"success": False, "error": "presupuesto y area deben ser mayores a 0"}), 400

        contexto_clima_suelo = _formatear_contexto_clima_suelo(datos_analisis)

        # Mismos parámetros técnicos que /plan-cultivo (tabla -> cache -> IA).
        parametros_crudos, origen_parametros = resolver_parametros_tecnicos(
            cultivo, departamento, municipio, contexto_clima_suelo
        )
        error_busqueda = parametros_crudos.get("error") if isinstance(parametros_crudos, dict) else "respuesta no era un dict"

        # Aptitud SOLO informativa (no bloquea el cálculo en modo validación).
        apto = parametros_crudos.get("apto_para_la_zona") if isinstance(parametros_crudos, dict) else None
        motivo_aptitud = parametros_crudos.get("motivo_aptitud") if isinstance(parametros_crudos, dict) else None

        parametros, campos_estimados = completar_parametros(parametros_crudos)

        # Mismo cálculo exacto que la versión real.
        precio_dane = _buscar_precio_dane_para_cultivo(cultivo, departamento, municipio)
        calculado = calcular_plan(parametros, presupuesto_cop, area_disponible_m2, precio_dane_kg=precio_dane)

        return jsonify({
            "success": True,
            "cultivo": cultivo,
            "ubicacion": f"{municipio}, {departamento}",
            "entrada": {
                "presupuesto_cop": presupuesto_cop,
                "area_m2": area_disponible_m2,
                "area_ha": round(area_disponible_m2 / 10000.0, 4),
                "unidad_original": unidad,
                "tipo_terreno": tipo_terreno,
            },
            "origen_parametros": origen_parametros,
            "error_busqueda": error_busqueda,
            "apto_para_la_zona": apto,
            "motivo_aptitud": motivo_aptitud,
            "precio_venta_kg_cop_usado": calculado.get("precio_kg_usado_cop"),
            "precio_fuente": calculado.get("precio_fuente"),
            "campos_estimados": campos_estimados,
            "parametros_tecnicos_usados": {
                "categoria_cultivo": parametros.get("categoria_cultivo"),
                "distancia_entre_surcos_m": parametros.get("distancia_entre_surcos_m"),
                "distancia_entre_plantas_m": parametros.get("distancia_entre_plantas_m"),
                "costo_semilla_o_plantula_unidad_cop": parametros.get("costo_semilla_o_plantula_unidad_cop"),
                "costo_preparacion_terreno_por_ha_cop": parametros.get("costo_preparacion_terreno_por_ha_cop"),
                "costo_fertilizantes_por_ha_cop": parametros.get("costo_fertilizantes_por_ha_cop"),
                "costo_agroquimicos_control_plagas_por_ha_cop": parametros.get("costo_agroquimicos_control_plagas_por_ha_cop"),
                "jornales_necesarios_por_ha_ciclo": parametros.get("jornales_necesarios_por_ha_ciclo"),
                "valor_jornal_cop": parametros.get("valor_jornal_cop"),
                "rendimiento_estimado_kg_por_planta": parametros.get("rendimiento_estimado_kg_por_planta"),
                "rendimiento_estimado_kg_por_ha": parametros.get("rendimiento_estimado_kg_por_ha"),
                "ciclo_productivo_meses": parametros.get("ciclo_productivo_meses"),
                "fuentes_consultadas": parametros.get("fuentes_consultadas", []),
            },
            "resultado": calculado,
        })

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