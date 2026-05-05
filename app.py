import os
from flask import Flask, jsonify
from flask_cors import CORS
from zeep import Client
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

WSDL_URL = "http://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService?WSDL"

client = None

try:
    client = Client(WSDL_URL)
    print("✅ Conectado al SOAP del DANE")
except Exception as e:
    print(f"❌ Error SOAP: {e}")

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "soap_connected": client is not None
    })

@app.route("/debug")
def debug():

    if client is None:
        return jsonify({
            "success": False,
            "error": "No hay conexión SOAP"
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
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)