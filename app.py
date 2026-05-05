import os
from flask import Flask, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# === PUNTO CRÍTICO: Usted debe encontrar la URL real del CSV o API en Agronet ===
# Mientras tanto, este servicio funciona con datos de ejemplo para probar la conexión.
# No necesita el WSDL del DANE si usamos la fuente de Agronet (mucho más fácil).

PRECIOS_POR_PRODUCTO = {
    "papa": {"precio": 2500, "unidad": "kg", "plaza": "Corabastos"},
    "tomate": {"precio": 3200, "unidad": "kg", "plaza": "Corabastos"},
    "arroz": {"precio": 3800, "unidad": "kg", "plaza": "Corabastos"}
}

@app.route('/')
def home():
    return jsonify({"mensaje": "API de Precios Agrícolas", "status": "viva"})

@app.route('/precios/<producto>')
def get_precio(producto):
    producto = producto.lower()
    if producto in PRECIOS_POR_PRODUCTO:
        return jsonify(PRECIOS_POR_PRODUCTO[producto])
    else:
        return jsonify({"error": f"Producto '{producto}' no encontrado"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)