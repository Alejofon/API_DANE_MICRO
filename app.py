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
            "error": "No se pudo conectar al SOAP"
        })

    data = {
        "services": []
    }

    try:

        for service_name, service in client.wsdl.services.items():

            service_data = {
                "service": service_name,
                "ports": []
            }

            for port_name, port in service.ports.items():

                port_data = {
                    "port": port_name,
                    "operations": []
                }

                operations = port.binding._operations

                for operation_name, operation in operations.items():

                    op_data = {
                        "name": operation_name,
                        "input": str(operation.input.signature())
                    }

                    port_data["operations"].append(op_data)

                service_data["ports"].append(port_data)

            data["services"].append(service_data)

        return jsonify(data)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)