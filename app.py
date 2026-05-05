from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        "mensaje": "SIPSA Bridge funcionando",
        "status": "online"
    })

@app.route('/precios/<producto>')
def get_precio(producto):
    precios = {
        "papa": 2500, "tomate": 3200, "arroz": 3800,
        "yuca": 1800, "platano": 2200, "cebolla": 2800
    }
    
    if producto.lower() in precios:
        return jsonify({
            "success": True,
            "producto": producto,
            "precio_kg": precios[producto.lower()]
        })
    else:
        return jsonify({"success": False}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)