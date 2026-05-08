import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from services.soil_service import get_soil_data

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
        "message": "API DANE - Precios SIPSA",
        "endpoints": {
            "productos": "/productos",
            "productos_con_precios": "/productos?precio_min=1000&precio_max=5000",
            "producto_especifico": "/producto/aguacate",
            "departamentos": "/departamentos",
            "departamento_especifico": "/departamento/BOGOTA",
            "grupos": "/grupos",
            "estadisticas": "/estadisticas",
            "fecha_especifica": "/fecha/2024-01-01",
            "rango_fechas": "/rango-fechas?inicio=2024-01-01&fin=2024-12-31"
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
# START APP
# -----------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)