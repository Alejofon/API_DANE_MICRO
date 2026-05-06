import os
import logging
import psycopg2

from flask import Flask, jsonify
from flask_cors import CORS

from zeep import Client
from zeep.transports import Transport

from requests import Session



# -----------------------------------
# CONFIGURACIÓN FLASK
# -----------------------------------

app = Flask(__name__)
CORS(app)

# -----------------------------------
# CONEXIÓN POSTGRESQL
# -----------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

db_connected = False

try:

    conn = psycopg2.connect(DATABASE_URL)

    cursor = conn.cursor()

    cursor.execute("SELECT version();")

    version = cursor.fetchone()

    print("✅ PostgreSQL conectado")
    print(version)

    db_connected = True

    cursor.close()
    conn.close()

except Exception as e:

    print(f"❌ Error PostgreSQL: {e}")

# -----------------------------------

logging.basicConfig(level=logging.INFO)

# -----------------------------------
# WSDL DEL DANE
# -----------------------------------

WSDL_URL = "http://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService?WSDL"

# -----------------------------------
# CONFIGURAR CLIENTE SOAP
# -----------------------------------

client = None

try:

    # Crear sesión HTTP
    session = Session()

    # Crear transporte para Zeep
    transport = Transport(session=session)

    # Crear cliente SOAP
    client = Client(
        wsdl=WSDL_URL,
        transport=transport
    )

    # FORZAR endpoint manualmente
    client.service._binding_options["address"] = (
        "https://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService"
    )

    print("✅ Cliente SOAP conectado")

except Exception as e:

    print(f"❌ Error creando cliente SOAP: {e}")

# -----------------------------------
# RUTA PRINCIPAL
# -----------------------------------

@app.route("/")
def home():

    return jsonify({
    "status": "online",
    "soap_connected": client is not None,
    "postgres_connected": db_connected
})

# -----------------------------------
# TEST SOAP
# -----------------------------------

@app.route("/test")
def test():

    try:

        result = client.service.promediosSipsaParcial()

        first_item = None

        for item in result:

            first_item = item
            break

        if first_item is None:

            return jsonify({
                "success": False,
                "error": "No se encontraron registros"
            })

        return jsonify({
            "success": True,
            "type": str(type(first_item)),
            "data": str(first_item)
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })
# -----------------------------------
# DEBUG INFO
# -----------------------------------

@app.route("/debug")
def debug():

    if client is None:

        return jsonify({
            "success": False,
            "error": "Cliente SOAP no inicializado"
        })

    try:

        services = {}

        for service_name, service in client.wsdl.services.items():

            services[service_name] = {}

            for port_name, port in service.ports.items():

                services[service_name][port_name] = {
                    "binding_name": str(port.binding.name),
                    "location": port.binding_options.get("address"),
                    "operations": list(port.binding._operations.keys())
                }

        return jsonify({
            "success": True,
            "services": services
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })
    
#-----------------------------------
#Create table
#-----------------------------------
@app.route("/create-table")
def create_table():

    try:

        conn = psycopg2.connect(DATABASE_URL)

        cursor = conn.cursor()

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS precios_agro (

                id SERIAL PRIMARY KEY,

                producto TEXT,

                ciudad TEXT,

                precio NUMERIC,

                fecha_consulta DATE,

                fuente TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            );

        """)

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Tabla creada correctamente"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })
    
#-----------------------------------
# Insertar datos de prueba
#-----------------------------------
@app.route("/insert-test")
def insert_test():

    try:

        conn = psycopg2.connect(DATABASE_URL)

        cursor = conn.cursor()

        cursor.execute("""

            INSERT INTO precios_agro (
                producto,
                ciudad,
                precio,
                fecha_consulta,
                fuente
            )

            VALUES (
                %s,
                %s,
                %s,
                CURRENT_DATE,
                %s
            )

        """, (
            "cebolla",
            "Bogotá",
            2500,
            "DANE"
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Registro insertado"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })
    
#-----------------------------------
# Consultar datos de prueba
#-----------------------------------
@app.route("/data")
def get_data():

    try:

        conn = psycopg2.connect(DATABASE_URL)

        cursor = conn.cursor()

        cursor.execute("""

            SELECT
                id,
                producto,
                ciudad,
                precio,
                fecha_consulta,
                fuente,
                created_at

            FROM precios_agro

            ORDER BY id DESC

            LIMIT 20;

        """)

        rows = cursor.fetchall()

        data = []

        for row in rows:

            data.append({
                "id": row[0],
                "producto": row[1],
                "ciudad": row[2],
                "precio": float(row[3]),
                "fecha_consulta": str(row[4]),
                "fuente": row[5],
                "created_at": str(row[6])
            })

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "total": len(data),
            "data": data
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })
# -----------------------------------
# Operation
# -----------------------------------

@app.route("/operations")
def operations():

    try:

        operations = {}

        binding = client.wsdl.bindings[
            '{http://servicios.sipsa.co.gov.dane/}SrvSipsaUpraPortBinding'
        ]

        for op_name, operation in binding._operations.items():

            operations[op_name] = {
                "input": str(operation.input.signature()),
                "output": str(operation.output.signature())
            }

        return jsonify({
            "success": True,
            "operations": operations
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })

# -----------------------------------
# INICIO APP
# -----------------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )