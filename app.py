import os
from flask import Flask, jsonify
from flask_cors import CORS
from zeep import Client
from zeep.exceptions import Fault, TransportError
import logging

app = Flask(__name__)
CORS(app)

# Configurar logging para ver errores
logging.basicConfig(level=logging.INFO)

# WSDL del servicio SIPSA del DANE
WSDL_URL = "http://appweb.dane.gov.co/sipsaWS/SrvSipsaUpraBeanService?WSDL"

# Intentar crear el cliente
try:
    client = Client(WSDL_URL)
    print("✅ Cliente SOAP conectado al DANE correctamente")
    print(f"Servicios disponibles: {[service for service in client.wsdl.services]}")
except Exception as e:
    print(f"❌ Error conectando al DANE: {e}")
    client = None

@app.route('/')
def home():
    return jsonify({
        "mensaje": "API SIPSA - DANE",
        "status": "online",
        "wsdl": WSDL_URL,
        "conexion_dane": client is not None
    })

@app.route('/precios/<producto>')
def get_precio_dane(producto):
    if client is None:
        return jsonify({
            "success": False,
            "error": "No hay conexión con el servicio del DANE",
            "solucion": "Revisar que el WSDL esté accesible"
        }), 503
    
    try:
        # Ver qué operaciones tiene el servicio
        # Esta línea ayuda a debuggear
        print(f"Operaciones disponibles: {[method for method in dir(client.service) if not method.startswith('_')]}")
        
        # Intento de llamada al servicio (ajustar según operación real)
        # NOTA: El método exacto puede variar, esto es un intento
        resultado = client.service.consultarPreciosMayoristas(
            codProducto=producto
        )
        
        return jsonify({
            "success": True,
            "fuente": "DANE - SIPSA",
            "producto": producto,
            "data": str(resultado)  # Temporal para ver qué devuelve
        })
        
    except Fault as e:
        return jsonify({
            "success": False,
            "error": f"Error en servicio DANE: {e.message}",
            "code": e.code
        }), 400
    except TransportError as e:
        return jsonify({
            "success": False,
            "error": f"Error de conexión: {e}",
            "sugerencia": "El WSDL puede no estar accesible momentáneamente"
        }), 503
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error inesperado: {str(e)}"
        }), 500

@app.route('/debug')
def debug_dane():
    """Endpoint para depurar la conexión con el DANE"""
    if client is None:
        return jsonify({"error": "Cliente no inicializado"}), 500
    
    info = {
        "wsdl_url": WSDL_URL,
        "services": [],
        "operations": []
    }
    
    try:
        # Listar servicios disponibles
        for service in client.wsdl.services:
            info["services"].append(service.name)
            for port in service.ports:
                for operation in port.binding._operations.values():
                    info["operations"].append({
                        "name": operation.name,
                        "input": str(operation.input.signature()) if hasattr(operation.input, 'signature') else "unknown"
                    })
    except Exception as e:
        info["error"] = str(e)
    
    return jsonify(info)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)