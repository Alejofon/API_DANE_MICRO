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

    if client is None:

        return jsonify({
            "success": False,
            "error": "Cliente SOAP no inicializado"
        })

    try:

        # probar con parámetro simple
        result = client.service.consultarInsumosSipsaMesMadr(1)

        return jsonify({
            "success": True,
            "type": str(type(result)),
            "data": str(result)[:3000]
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