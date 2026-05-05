from flask import Flask, jsonify
from flask_cors import CORS
from zeep import Client
from zeep.exceptions import Fault, TransportError

app = Flask(__name__)
CORS(app)

# La ubicación del WSDL del servicio SIPSA. Es pública.
WSDL_URL = "http://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService?WSDL"

# Intentar crear el cliente globalmente para que no se recree en cada consulta.
try:
    client = Client(WSDL_URL)
    print("Cliente SOAP creado correctamente.")
except Exception as e:
    print(f"ERROR FATAL: No se pudo crear el cliente SOAP: {e}")
    client = None

@app.route('/')
def home():
    return jsonify({
        "mensaje": "Microservicio SIPSA (DANE)",
        "status": "online"
    })

@app.route('/precios/<string:producto>')
def obtener_precio(producto):
    if client is None:
        return jsonify({"success": False, "error": "Cliente SOAP no disponible"}), 500

    try:
        # La llamada REAL al servicio del DANE.
        # Nota: Aquí es donde puede fallar si el método o parámetros son inexactos.
        # He documentado el problema, pero esta es la sintaxis esperada.
        resultado = client.service.consultarPreciosMayoristas(
            codProducto=producto  # Revisa la documentación del DANE, aquí puede ir otro nombre.
        )
        
        # Si la llamada fue exitosa, resultado será un objeto complejo.
        # Lo transformamos a JSON simple.
        return jsonify({
            "success": True,
            "producto": producto,
            "data": str(resultado)  # Mientras aprendemos a parsearlo, vemos qué devuelve.
        })

    except Fault as e:
        # Error específico del servicio (ej. parámetro incorrecto)
        return jsonify({"success": False, "error": f"Error en servicio SOAP: {e.message}"}), 400
    except TransportError as e:
        # Error de red o del servidor del DANE
        return jsonify({"success": False, "error": f"Error de conexión con DANE: {e}"}), 503
    except Exception as e:
        return jsonify({"success": False, "error": f"Error inesperado: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)