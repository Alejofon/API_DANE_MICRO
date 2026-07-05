# services/redaccion_service.py
"""
Última etapa del flujo. Para cuando llegamos aquí, TODOS los números ya
fueron calculados por calculo_agricola.py con datos validados. Este
servicio solo le pide a gpt-4.1-mini (chat completions, igual que el
resto de la app, sin búsqueda web: no hace falta) que REDACTE la
explicación en español para el agricultor, reutilizando esas cifras
tal cual se le entregan.

Como defensa adicional (por si el modelo "corrige" un número por su
cuenta), después de recibir la respuesta el backend SOBRESCRIBE los
campos numéricos con los valores ya calculados en Python. El modelo
nunca tiene la última palabra sobre una cifra.
"""

import os
import json
import re
import requests

from .utils_numeros import formatear_cop

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODELO_REDACCION = "gpt-4.1-mini"


def plan_no_apto(cultivo, motivo, municipio, departamento):
    """
    Respuesta inmediata cuando agro_technical_service determinó que el
    cultivo NO es agronómicamente apto para la zona (ej. un cultivo tropical
    en un páramo frío). No se llama a ninguna IA aquí: no tiene sentido
    calcular costos/rendimientos de algo que no debería sembrarse ahí. Se
    devuelve el mismo esquema que espera project_detail_page.dart, pero
    con "No viable" y la razón real en vez de un plan completo.
    """
    motivo_texto = motivo or (
        f"{cultivo} no es agronómicamente compatible con el clima/suelo de "
        f"{municipio}, {departamento}."
    )
    return {
        "rentabilidad": {
            "nivel": "No viable",
            "descripcion": motivo_texto,
            "retorno_inversion_meses": None,
            "ganancia_estimada_por_cosecha": "No aplica",
            "area_realmente_cultivable": "No aplica",
            "numero_plantas_estimadas": 0,
            "distancia_siembra": "No aplica",
            "produccion_estimada": "No aplica",
            "area_minima_rentable": "No aplica",
            "presupuesto_minimo_recomendado": "No aplica",
        },
        "siembra_estimada": {
            "area_recomendada_siembra": "No aplica",
            "numero_plantas_estimadas": 0,
            "distancia_siembra": "No aplica",
            "produccion_estimada": "No aplica",
            "area_minima_rentable": "No aplica",
            "presupuesto_minimo_recomendado": "No aplica",
        },
        "dificultad": {
            "nivel": "Alta",
            "descripcion": (
                "No se recomienda continuar con este cultivo en esta zona por "
                "incompatibilidad agronómica. " + motivo_texto
            ),
        },
        "tiempos": {
            "siembra_mejor_epoca": "No aplica",
            "cosecha_meses": 0,
            "calendario_riego": "No aplica",
            "calendario_fertilizacion": "No aplica",
        },
        "plagas": [],
        "mercado": {
            "precio_actual_kg": "No aplica",
            "canales_venta": [],
            "compradores": [],
            "tendencias": "No aplica",
        },
        "beneficios": [],
        "pasos_siembra": [],
    }


def _extraer_json(texto):
    if not texto:
        return None
    limpio = texto.strip()
    limpio = re.sub(r"^```(json)?", "", limpio, flags=re.IGNORECASE).strip()
    limpio = re.sub(r"```$", "", limpio).strip()
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        inicio, fin = limpio.find("{"), limpio.rfind("}")
        if inicio != -1 and fin != -1 and fin > inicio:
            try:
                return json.loads(limpio[inicio:fin + 1])
            except json.JSONDecodeError:
                return None
    return None


def _construir_prompt(cultivo, ubicacion, ui, calculado, parametros, advertencia, ganancia_atipica=False):
    nota_advertencia = ""
    if advertencia:
        nota_advertencia = (
            "\nNOTA: Los datos técnicos de este cultivo no pudieron verificarse "
            "en fuentes web y se usaron valores genéricos conservadores de "
            "respaldo. Menciónalo brevemente en la descripción de rentabilidad, "
            "sin alarmar al usuario, invitándolo a validar con un técnico local.\n"
        )

    nota_ganancia_atipica = ""
    if ganancia_atipica:
        nota_ganancia_atipica = (
            "\nNOTA: La ganancia estimada resultó inusualmente alta respecto a la "
            "inversión (más de 10 veces). Aunque la cifra ya está calculada y no "
            "debes cambiarla, menciona brevemente que esta cifra es atípica y que "
            "conviene verificarla con un técnico local antes de invertir.\n"
        )

    return f"""
Eres un ingeniero agrónomo colombiano. Tu ÚNICO trabajo es REDACTAR texto
explicativo en español para un agricultor. NO debes calcular ni cambiar
ninguna cifra: todas las que se te dan a continuación ya fueron calculadas
y son definitivas. Tu tarea es explicarlas con claridad y dar contexto
cualitativo (plagas, calendario, mercado, beneficios, pasos de siembra).
{nota_advertencia}{nota_ganancia_atipica}
CULTIVO: {cultivo}
UBICACIÓN: {ubicacion}

CIFRAS YA CALCULADAS (no las cambies, solo redáctalas o inclúyelas tal cual):
- Nivel de rentabilidad: {ui['nivel_rentabilidad']}
- Área recomendada a sembrar: {ui['area_realmente_cultivable']}
- Número de plantas estimadas: {ui['numero_plantas_estimadas']}
- Distancia de siembra: {ui['distancia_siembra']}
- Producción estimada: {ui['produccion_estimada']}
- Ganancia estimada por cosecha: {ui['ganancia_estimada_por_cosecha']}
- Retorno de inversión: {ui['retorno_inversion_meses']} meses (null si no hay retorno positivo)
- Área mínima rentable: {ui['area_minima_rentable']}
- Presupuesto mínimo recomendado: {ui['presupuesto_minimo_recomendado']}
- Ciclo productivo: {calculado['ciclo_productivo_meses']} meses
- Precio de venta usado: {formatear_cop(calculado['precio_kg_usado_cop'])}/kg (fuente: {calculado['precio_fuente']})

DATOS TÉCNICOS DE REFERENCIA (para redactar plagas/calendario/beneficios):
- Época de siembra recomendada: {parametros.get('epoca_siembra_recomendada')}
- Calendario de riego: {parametros.get('calendario_riego')}
- Calendario de fertilización: {parametros.get('calendario_fertilizacion')}
- Plagas comunes conocidas: {json.dumps(parametros.get('plagas_comunes', []), ensure_ascii=False)}
- Beneficios conocidos: {json.dumps(parametros.get('beneficios_cultivo', []), ensure_ascii=False)}

Responde EXCLUSIVAMENTE con este JSON (sin texto adicional, sin marcadores de código).
Puedes repetir las cifras dadas arriba en los campos numéricos, pero NO las alteres:

{{
  "rentabilidad": {{
    "nivel": "{ui['nivel_rentabilidad']}",
    "descripcion": "texto explicando POR QUÉ, basado en las cifras dadas",
    "retorno_inversion_meses": {json.dumps(ui['retorno_inversion_meses'])},
    "ganancia_estimada_por_cosecha": "{ui['ganancia_estimada_por_cosecha']}",
    "area_realmente_cultivable": "{ui['area_realmente_cultivable']}",
    "numero_plantas_estimadas": {ui['numero_plantas_estimadas']},
    "distancia_siembra": "{ui['distancia_siembra']}",
    "produccion_estimada": "{ui['produccion_estimada']}",
    "area_minima_rentable": "{ui['area_minima_rentable']}",
    "presupuesto_minimo_recomendado": "{ui['presupuesto_minimo_recomendado']}"
  }},
  "siembra_estimada": {{
    "area_recomendada_siembra": "{ui['area_realmente_cultivable']}",
    "numero_plantas_estimadas": {ui['numero_plantas_estimadas']},
    "distancia_siembra": "{ui['distancia_siembra']}",
    "produccion_estimada": "{ui['produccion_estimada']}",
    "area_minima_rentable": "{ui['area_minima_rentable']}",
    "presupuesto_minimo_recomendado": "{ui['presupuesto_minimo_recomendado']}"
  }},
  "dificultad": {{
    "nivel": "Alta | Media | Baja",
    "descripcion": "texto técnico"
  }},
  "tiempos": {{
    "siembra_mejor_epoca": "texto",
    "cosecha_meses": {calculado['ciclo_productivo_meses']},
    "calendario_riego": "texto",
    "calendario_fertilizacion": "texto"
  }},
  "plagas": [
    {{"nombre": "texto", "sintomas": "texto", "control": "texto", "epoca_riesgo": "texto"}}
  ],
  "mercado": {{
    "precio_actual_kg": "{formatear_cop(calculado['precio_kg_usado_cop'])}",
    "canales_venta": ["texto"],
    "compradores": [],
    "tendencias": "texto basado en contexto colombiano"
  }},
  "beneficios": ["texto"],
  "pasos_siembra": ["texto"]
}}
"""


def _sobrescribir_numeros(plan, ui, calculado):
    """
    Defensa en profundidad: sin importar lo que haya escrito el modelo,
    los campos numéricos/cuantitativos quedan con el valor calculado en
    Python. El modelo solo aporta las descripciones cualitativas.
    """
    rentabilidad = plan.setdefault("rentabilidad", {})
    rentabilidad["nivel"] = ui["nivel_rentabilidad"]
    rentabilidad["retorno_inversion_meses"] = ui["retorno_inversion_meses"]
    rentabilidad["ganancia_estimada_por_cosecha"] = ui["ganancia_estimada_por_cosecha"]
    rentabilidad["area_realmente_cultivable"] = ui["area_realmente_cultivable"]
    rentabilidad["numero_plantas_estimadas"] = ui["numero_plantas_estimadas"]
    rentabilidad["distancia_siembra"] = ui["distancia_siembra"]
    rentabilidad["produccion_estimada"] = ui["produccion_estimada"]
    rentabilidad["area_minima_rentable"] = ui["area_minima_rentable"]
    rentabilidad["presupuesto_minimo_recomendado"] = ui["presupuesto_minimo_recomendado"]

    siembra = plan.setdefault("siembra_estimada", {})
    siembra["area_recomendada_siembra"] = ui["area_realmente_cultivable"]
    siembra["numero_plantas_estimadas"] = ui["numero_plantas_estimadas"]
    siembra["distancia_siembra"] = ui["distancia_siembra"]
    siembra["produccion_estimada"] = ui["produccion_estimada"]
    siembra["area_minima_rentable"] = ui["area_minima_rentable"]
    siembra["presupuesto_minimo_recomendado"] = ui["presupuesto_minimo_recomendado"]

    tiempos = plan.setdefault("tiempos", {})
    tiempos["cosecha_meses"] = calculado["ciclo_productivo_meses"]

    mercado = plan.setdefault("mercado", {})
    mercado["precio_actual_kg"] = formatear_cop(calculado["precio_kg_usado_cop"])

    return plan


def _plan_minimo(ui, calculado):
    """Plan de emergencia si incluso la redacción falla, para no romper la app."""
    descripcion = (
        calculado.get("motivo_no_viable")
        or "No se pudo generar una descripción detallada (falla temporal del servicio de redacción); "
           "las cifras numéricas sí están calculadas y son confiables."
    )
    plan = {
        "rentabilidad": {"descripcion": descripcion},
        "siembra_estimada": {},
        "dificultad": {"nivel": "Media", "descripcion": "No se pudo generar una descripción detallada."},
        "tiempos": {
            "siembra_mejor_epoca": "No disponible",
            "cosecha_meses": calculado["ciclo_productivo_meses"],
            "calendario_riego": "No disponible",
            "calendario_fertilizacion": "No disponible",
        },
        "plagas": [],
        "mercado": {"precio_actual_kg": "No disponible", "canales_venta": [], "compradores": [], "tendencias": "No disponible"},
        "beneficios": [],
        "pasos_siembra": [],
    }
    return _sobrescribir_numeros(plan, ui, calculado)


def redactar_plan_final(cultivo, ubicacion, ui, calculado, parametros, advertencia=False, ganancia_atipica=False):
    """
    Devuelve el dict final EXACTAMENTE con el esquema que espera
    project_detail_page.dart / parsePlanResponse en Flutter.
    """
    if not OPENAI_API_KEY:
        return _plan_minimo(ui, calculado)

    prompt = _construir_prompt(cultivo, ubicacion, ui, calculado, parametros, advertencia, ganancia_atipica)

    try:
        resp = requests.post(
            OPENAI_CHAT_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
            json={
                "model": MODELO_REDACCION,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        contenido = data["choices"][0]["message"]["content"].strip()
    except (requests.exceptions.RequestException, KeyError, IndexError):
        return _plan_minimo(ui, calculado)

    plan = _extraer_json(contenido)
    if plan is None:
        return _plan_minimo(ui, calculado)

    return _sobrescribir_numeros(plan, ui, calculado)