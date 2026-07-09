# pruebas_validacion/common.py
"""
Utilidades compartidas por los scripts de pruebas de MiSiembra.

NO forma parte del backend en producción: es solo instrumentación de pruebas.
Todo apunta por defecto al backend desplegado en Render; se puede sobrescribir
con la variable de entorno PRUEBAS_BASE_URL (útil para probar contra localhost).
"""

import os
import sys
import json
import time
import statistics
from datetime import datetime

import requests

# Permite `from services.x import y` desde los scripts (repo root en el path).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

BASE_URL = os.getenv("PRUEBAS_BASE_URL", "https://api-dane-micro.onrender.com").rstrip("/")

DIR_RESULTADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")
os.makedirs(DIR_RESULTADOS, exist_ok=True)

# Coordenadas reales aproximadas de los municipios usados en las pruebas
# (lat, lon). La altitud se consulta en vivo a Open-Meteo cuando se necesita.
ZONAS = {
    "Turmequé": {"departamento": "BOYACA", "municipio": "TURMEQUE", "lat": 5.3253, "lon": -73.4936},
    "Villavicencio": {"departamento": "META", "municipio": "VILLAVICENCIO", "lat": 4.1420, "lon": -73.6266},
    "Tocancipá": {"departamento": "CUNDINAMARCA", "municipio": "TOCANCIPA", "lat": 5.0573, "lon": -73.9116},
    "Chocontá": {"departamento": "CUNDINAMARCA", "municipio": "CHOCONTA", "lat": 5.1458, "lon": -73.6854},
    "Florencia": {"departamento": "CAQUETA", "municipio": "FLORENCIA", "lat": 1.6144, "lon": -75.6062},
    "Santa Marta": {"departamento": "MAGDALENA", "municipio": "SANTA MARTA", "lat": 11.2408, "lon": -74.1990},
    "Pasto": {"departamento": "NARINO", "municipio": "PASTO", "lat": 1.2136, "lon": -77.2811},
    "Armenia": {"departamento": "QUINDIO", "municipio": "ARMENIA", "lat": 4.5339, "lon": -75.6811},
    "Valledupar": {"departamento": "CESAR", "municipio": "VALLEDUPAR", "lat": 10.4631, "lon": -73.2532},
    "Medellín": {"departamento": "ANTIOQUIA", "municipio": "MEDELLIN", "lat": 6.2442, "lon": -75.5812},
}


def ahora_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timed_get(path, params=None, timeout=300):
    """GET con medición. Retorna (status, elapsed_ms, json|None, error|None)."""
    url = f"{BASE_URL}{path}"
    t0 = time.perf_counter()
    try:
        r = requests.get(url, params=params, timeout=timeout)
        elapsed = (time.perf_counter() - t0) * 1000.0
        try:
            data = r.json()
        except ValueError:
            data = None
        return r.status_code, elapsed, data, None
    except requests.RequestException as e:
        elapsed = (time.perf_counter() - t0) * 1000.0
        return None, elapsed, None, str(e)


def timed_post(path, body, timeout=300):
    """POST JSON con medición. Retorna (status, elapsed_ms, json|None, error|None)."""
    url = f"{BASE_URL}{path}"
    t0 = time.perf_counter()
    try:
        r = requests.post(url, json=body, timeout=timeout)
        elapsed = (time.perf_counter() - t0) * 1000.0
        try:
            data = r.json()
        except ValueError:
            data = None
        return r.status_code, elapsed, data, None
    except requests.RequestException as e:
        elapsed = (time.perf_counter() - t0) * 1000.0
        return None, elapsed, None, str(e)


def warmup():
    """Despierta el servicio de Render (plan gratuito duerme). Se descarta."""
    print(f"[warmup] Despertando {BASE_URL} (puede tardar ~1 min si está dormido)...")
    status, elapsed, _, err = timed_get("/", timeout=120)
    print(f"[warmup] GET / -> {status} en {elapsed/1000:.1f}s {('· ' + err) if err else ''}")
    return status == 200


def resumen_estadistico(muestras_ms):
    """avg, min, max, p95 de una lista de tiempos en ms."""
    if not muestras_ms:
        return {"n": 0, "promedio_ms": None, "min_ms": None, "max_ms": None, "p95_ms": None}
    ordenados = sorted(muestras_ms)
    # p95 por método de rango más cercano (suficiente para n pequeño).
    idx = max(0, min(len(ordenados) - 1, round(0.95 * (len(ordenados) - 1))))
    return {
        "n": len(muestras_ms),
        "promedio_ms": round(statistics.mean(muestras_ms), 1),
        "min_ms": round(min(muestras_ms), 1),
        "max_ms": round(max(muestras_ms), 1),
        "p95_ms": round(ordenados[idx], 1),
    }


def guardar_json(nombre, data):
    ruta = os.path.join(DIR_RESULTADOS, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return ruta


def guardar_texto(nombre, texto):
    ruta = os.path.join(DIR_RESULTADOS, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)
    return ruta


def obtener_altitud(lat, lon):
    """Altitud real de la zona (Open-Meteo), misma fuente que clima_service."""
    try:
        from services.clima_service import get_elevation
        return get_elevation(lat, lon)
    except Exception:
        # Fallback directo a la API pública si no se puede importar el service.
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/elevation",
                params={"latitude": lat, "longitude": lon}, timeout=30,
            )
            return r.json().get("elevation", [None])[0]
        except Exception:
            return None
