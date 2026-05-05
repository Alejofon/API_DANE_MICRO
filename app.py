import os
import logging

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
        "soap_connected": client is not None
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

        result = client.service.promediosSipsaCiudad()

        # Convertir a lista pequeña
        sample = []

        count = 0

        for item in result:

            sample.append(str(item))

            count += 1

            if count >= 5:
                break

        return jsonify({
            "success": True,
            "total_muestra": len(sample),
            "sample": sample
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

# -----------------------------------
# INICIO APP
# -----------------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )