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

        resultado = client.service.promediosSipsaCiudad()

        return jsonify({
            "success": True,
            "tipo": str(type(resultado)),
            "data": str(resultado)[:5000]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)