# services/cache_tecnico_service.py
"""
Cache persistente en Postgres de parámetros técnicos ya resueltos por la IA
de búsqueda (agro_technical_service.py). No reemplaza la tabla curada
(tabla_referencia_cultivos.py) — es la red de seguridad para cultivos que NO
están en esa tabla: la primera vez que se pide un cultivo así en una zona
dada, se le pregunta a la IA y el resultado (ya validado) se guarda aquí.
Las siguientes consultas del MISMO cultivo en la MISMA zona ya no llaman a
la IA: salen de esta tabla, instantáneas y sin costo.
"""

import os
import json
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

# Pasado este tiempo, se vuelve a consultar la IA aunque exista en cache
# (los costos de insumos cambian; no queremos servir un dato de hace 3 años
# como si fuera vigente).
MESES_VIGENCIA_CACHE = 12


def _conectar():
    return psycopg2.connect(DATABASE_URL)


def asegurar_tabla():
    """Crea la tabla de cache si no existe. Idempotente y segura de llamar en cada arranque."""
    try:
        conn = _conectar()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS parametros_cultivo_cache (
                id SERIAL PRIMARY KEY,
                cultivo_normalizado VARCHAR(200) NOT NULL,
                departamento VARCHAR(150) NOT NULL,
                municipio VARCHAR(150) NOT NULL,
                parametros JSONB NOT NULL,
                origen VARCHAR(30) NOT NULL DEFAULT 'ia_busqueda',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (cultivo_normalizado, departamento, municipio)
            )
            """
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[cache_tecnico_service] No se pudo asegurar la tabla de cache: {e}")


def _clave(cultivo, departamento, municipio):
    return (
        (cultivo or "").strip().lower(),
        (departamento or "").strip().upper(),
        (municipio or "").strip().upper(),
    )


def obtener(cultivo, departamento, municipio):
    """Retorna el dict de parámetros cacheados (si está vigente) o None."""
    cultivo_norm, depto_norm, muni_norm = _clave(cultivo, departamento, municipio)
    if not cultivo_norm or not depto_norm or not muni_norm:
        return None
    try:
        conn = _conectar()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT parametros, fecha_actualizacion FROM parametros_cultivo_cache
            WHERE cultivo_normalizado = %s AND departamento = %s AND municipio = %s
            """,
            (cultivo_norm, depto_norm, muni_norm),
        )
        fila = cur.fetchone()
        cur.close()
        conn.close()
        if not fila:
            return None
        vencimiento = fila["fecha_actualizacion"] + timedelta(days=30 * MESES_VIGENCIA_CACHE)
        if datetime.now() > vencimiento:
            return None
        return fila["parametros"]
    except Exception as e:
        print(f"[cache_tecnico_service] Error leyendo cache: {e}")
        return None


def obtener_candidatos(departamento, municipio, bracket):
    """
    Lee un SET de candidatos cacheado para (zona, bracket de intensidad).
    Reutiliza la misma tabla usando una clave especial en cultivo_normalizado.
    Retorna la lista de candidatos o None.
    """
    clave_especial = f"__opciones__:{bracket}"
    guardado = obtener(clave_especial, departamento, municipio)
    if isinstance(guardado, dict):
        candidatos = guardado.get("candidatos")
        if isinstance(candidatos, list) and candidatos:
            return candidatos
    return None


def guardar_candidatos(departamento, municipio, bracket, candidatos):
    """
    Guarda un set de candidatos para (zona, bracket de intensidad) Y además
    persiste cada candidato individualmente en el cache por-cultivo, para que
    si el usuario luego pide el plan detallado de uno de esos cultivos novedosos
    (/plan-cultivo) salga del cache al instante en vez de disparar otra llamada
    de IA.
    """
    clave_especial = f"__opciones__:{bracket}"
    guardar(clave_especial, departamento, municipio, {"candidatos": candidatos}, origen="ia_candidatos")

    for candidato in candidatos:
        if not isinstance(candidato, dict):
            continue
        nombre = str(candidato.get("nombre_cultivo", "")).strip()
        if nombre:
            guardar(nombre, departamento, municipio, candidato, origen="ia_candidatos")


def guardar(cultivo, departamento, municipio, parametros, origen="ia_busqueda"):
    """Guarda/actualiza (upsert) los parámetros resueltos para no volver a llamar la IA."""
    cultivo_norm, depto_norm, muni_norm = _clave(cultivo, departamento, municipio)
    if not cultivo_norm or not depto_norm or not muni_norm:
        return
    try:
        conn = _conectar()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO parametros_cultivo_cache
                (cultivo_normalizado, departamento, municipio, parametros, origen, fecha_actualizacion)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (cultivo_normalizado, departamento, municipio)
            DO UPDATE SET parametros = EXCLUDED.parametros,
                          origen = EXCLUDED.origen,
                          fecha_actualizacion = CURRENT_TIMESTAMP
            """,
            (cultivo_norm, depto_norm, muni_norm, json.dumps(parametros), origen),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[cache_tecnico_service] Error guardando cache: {e}")
