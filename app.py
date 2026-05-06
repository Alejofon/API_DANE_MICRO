import os
import ast
import psycopg2

from flask import Flask, jsonify
from flask_cors import CORS

# -----------------------------------
# CONFIG FLASK
# -----------------------------------

app = Flask(__name__)
CORS(app)

# -----------------------------------
# DATABASE
# -----------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

# -----------------------------------
# HOME
# -----------------------------------

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "message": "API DANE online"
    })

# -----------------------------------
# CONSULTAR DATOS
# -----------------------------------

@app.route("/data")
def get_data():

    try:

        conn = psycopg2.connect(DATABASE_URL)

        cursor = conn.cursor()

        cursor.execute("""

            SELECT
                id,
                data

            FROM dane_raw

            ORDER BY id DESC

            LIMIT 100;

        """)

        rows = cursor.fetchall()

        results = []

        for row in rows:

            row_id = row[0]

            raw_data = row[1]

            try:

                # Convertir string a diccionario
                parsed = ast.literal_eval(raw_data)

                item = {
                    "id": row_id,
                    "producto": parsed.get("artiNombre"),
                    "grupo": parsed.get("grupNombre"),
                    "departamento": parsed.get("deptNombre"),
                    "municipio": parsed.get("muniNombre"),
                    "fuente": parsed.get("fuenNombre"),
                    "precio_min": str(parsed.get("minimoKg")),
                    "precio_max": str(parsed.get("maximoKg")),
                    "precio_promedio": str(parsed.get("promedioKg")),
                    "fecha": str(parsed.get("enmaFecha"))
                }

                results.append(item)

            except Exception as parse_error:

                results.append({
                    "id": row_id,
                    "error": str(parse_error)
                })

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "total": len(results),
            "data": results
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })

# -----------------------------------
# FILTRAR POR PRODUCTO
# -----------------------------------

@app.route("/producto/<nombre>")
def buscar_producto(nombre):

    try:

        conn = psycopg2.connect(DATABASE_URL)

        cursor = conn.cursor()

        cursor.execute("""

            SELECT
                id,
                data

            FROM dane_raw

            WHERE data ILIKE %s

            LIMIT 100;

        """, (f"%{nombre}%",))

        rows = cursor.fetchall()

        results = []

        for row in rows:

            raw_data = row[1]

            try:

                parsed = ast.literal_eval(raw_data)

                results.append({
                    "producto": parsed.get("artiNombre"),
                    "grupo": parsed.get("grupNombre"),
                    "municipio": parsed.get("muniNombre"),
                    "precio_promedio": str(parsed.get("promedioKg")),
                    "fecha": str(parsed.get("enmaFecha"))
                })

            except:
                pass

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "producto": nombre,
            "total": len(results),
            "data": results
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })

# -----------------------------------
# START APP
# -----------------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )