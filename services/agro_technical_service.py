# services/agro_technical_service.py
"""
Este servicio NO calcula nada y NO redacta texto para el usuario final.
Su único trabajo es: dado un cultivo y un contexto (ubicación, clima, suelo),
buscar en internet -restringido a fuentes técnicas agrícolas confiables- los
PARÁMETROS crudos que el backend necesita para hacer matemáticas:
distancias de siembra, costos de establecimiento por hectárea, jornales,
rendimiento esperado, ciclo productivo, plagas comunes, etc.

Usa la Responses API de OpenAI con la herramienta oficial `web_search`
(no scraping, no Selenium, no BeautifulSoup), restringida mediante
`filters.allowed_domains` a dominios técnicos/gubernamentales.

Devuelve SIEMPRE un dict de Python. Si algo falla, devuelve
{"error": "..."} y el llamador decide qué hacer (reintentar o usar
el fallback conservador de calculo_agricola.py).
"""

import os
import json
import re
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

# Modelo con capacidad de búsqueda web. Se usa gpt-4.1 (no -mini) para esta
# etapa porque es la que sostiene todos los cálculos posteriores; el ahorro
# de costo se hace en la etapa de redacción (redaccion_service.py), que sí
# usa gpt-4.1-mini como el resto de la app.
MODELO_BUSQUEDA = "gpt-4.1"

# Fuentes técnicas confiables. Se restringe la búsqueda web a estos dominios
# (la restricción incluye subdominios automáticamente, ej: 'gov.co' abajo
# también cubre 'ica.gov.co', 'minagricultura.gov.co', etc. si se agregan).
# Ampliar esta lista es la única forma soportada de "agregar más fuentes";
# no hay scraping de sitios fuera de esta lista.
DOMINIOS_CONFIABLES = [
    "agrosavia.co",
    "agronet.gov.co",
    "ica.gov.co",
    "upra.gov.co",
    "fao.org",
    "minagricultura.gov.co",
    "dane.gov.co",
    "sena.edu.co",
    "unal.edu.co",
    "corpoica.org.co",
    "cci.org.co",              # Corporación Colombia Internacional
    "fenalce.org",             # Federación Nacional de Cultivadores de Cereales
    "asohofrucol.com.co",
    "fedepapa.com",
]

CAMPOS_REQUERIDOS = [
    "categoria_cultivo",
    "distancia_entre_surcos_m",
    "distancia_entre_plantas_m",
    "costo_semilla_o_plantula_unidad_cop",
    "costo_preparacion_terreno_por_ha_cop",
    "costo_fertilizantes_por_ha_cop",
    "costo_agroquimicos_control_plagas_por_ha_cop",
    "jornales_necesarios_por_ha_ciclo",
    "valor_jornal_cop",
    "rendimiento_estimado_kg_por_planta",
    "rendimiento_estimado_kg_por_ha",
    "ciclo_productivo_meses",
    "precio_venta_kg_cop",
    "epoca_siembra_recomendada",
    "calendario_riego",
    "calendario_fertilizacion",
    "plagas_comunes",
    "beneficios_cultivo",
    "fuentes_consultadas",
]


def _construir_prompt(cultivo, departamento, municipio, contexto_clima_suelo, correccion=None):
    contexto = f"\n\nCONTEXTO DE CLIMA Y SUELO YA MEDIDO EN LA ZONA:\n{contexto_clima_suelo}" if contexto_clima_suelo else ""
    nota_correccion = ""
    if correccion:
        nota_correccion = f"""
IMPORTANTE - CORRECCIÓN REQUERIDA:
Tu respuesta anterior tenía valores fuera de rangos técnicamente razonables:
{correccion}
Vuelve a buscar y corrige específicamente esos valores con cifras reales y verificables.
"""

    return f"""
Eres un asistente técnico que SOLO recopila datos agronómicos verificables mediante
búsqueda web. NO debes recomendar, NO debes redactar explicaciones para agricultores,
NO debes calcular nada. Tu única salida es un JSON con parámetros crudos.

CULTIVO A INVESTIGAR: {cultivo}
UBICACIÓN: {municipio}, {departamento}, Colombia
{contexto}
{nota_correccion}

Busca en fuentes técnicas (ICA, Agrosavia, Agronet, UPRA, FAO, Fenalce, Fedepapa,
Asohofrucol, universidades, SENA, gobernaciones/secretarías de agricultura) los
siguientes datos para este cultivo en Colombia. Si una fuente da un rango, usa el
punto medio. Si de verdad no hay dato disponible, usa null (nunca inventes un
número al azar).

Responde EXCLUSIVAMENTE con un JSON válido (sin texto adicional, sin marcadores
de código), con esta estructura EXACTA:

{{
  "categoria_cultivo": "ciclo_corto | semipermanente | arboreo_frutal | extensivo",
  "distancia_entre_surcos_m": número,
  "distancia_entre_plantas_m": número,
  "costo_semilla_o_plantula_unidad_cop": número,
  "costo_preparacion_terreno_por_ha_cop": número,
  "costo_fertilizantes_por_ha_cop": número,
  "costo_agroquimicos_control_plagas_por_ha_cop": número,
  "jornales_necesarios_por_ha_ciclo": número,
  "valor_jornal_cop": número,
  "rendimiento_estimado_kg_por_planta": número o null,
  "rendimiento_estimado_kg_por_ha": número o null,
  "ciclo_productivo_meses": número,
  "precio_venta_kg_cop": número o null,
  "epoca_siembra_recomendada": "texto",
  "calendario_riego": "texto",
  "calendario_fertilizacion": "texto",
  "plagas_comunes": [
    {{"nombre": "texto", "sintomas": "texto", "control": "texto", "epoca_riesgo": "texto"}}
  ],
  "beneficios_cultivo": ["texto", "texto"],
  "fuentes_consultadas": ["url1", "url2"]
}}
"""


def _extraer_texto_respuesta(data):
    """Extrae el texto de salida de la Responses API, sin asumir SDK oficial."""
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"]

    texto_partes = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for bloque in item.get("content", []):
                if bloque.get("type") in ("output_text", "text"):
                    texto_partes.append(bloque.get("text", ""))
    return "\n".join(texto_partes).strip()


def _extraer_json(texto):
    """Limpia posibles fences de markdown y parsea el primer objeto JSON encontrado."""
    if not texto:
        return None
    limpio = texto.strip()
    limpio = re.sub(r"^```(json)?", "", limpio.strip(), flags=re.IGNORECASE).strip()
    limpio = re.sub(r"```$", "", limpio.strip()).strip()

    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        pass

    inicio = limpio.find("{")
    fin = limpio.rfind("}")
    if inicio != -1 and fin != -1 and fin > inicio:
        try:
            return json.loads(limpio[inicio:fin + 1])
        except json.JSONDecodeError:
            return None
    return None


def obtener_parametros_tecnicos(cultivo, departamento, municipio, contexto_clima_suelo=None, correccion=None):
    """
    Devuelve un dict con los parámetros crudos del cultivo, o {"error": "..."}.
    No hace ningún cálculo: eso es responsabilidad de calculo_agricola.py.
    """
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY no configurada en el backend"}

    prompt = _construir_prompt(cultivo, departamento, municipio, contexto_clima_suelo, correccion)

    payload = {
        "model": MODELO_BUSQUEDA,
        "tools": [
            {
                "type": "web_search",
                "filters": {"allowed_domains": DOMINIOS_CONFIABLES},
            }
        ],
        "tool_choice": "auto",
        "input": prompt,
    }

    try:
        resp = requests.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error consultando el modelo de búsqueda: {e}"}

    texto = _extraer_texto_respuesta(data)
    parametros = _extraer_json(texto)

    if parametros is None:
        return {"error": "La IA de búsqueda no devolvió un JSON válido", "raw": texto[:500]}

    faltantes = [c for c in CAMPOS_REQUERIDOS if c not in parametros]
    if faltantes:
        return {"error": f"Faltan campos en la respuesta de la IA: {faltantes}", "parcial": parametros}

    return parametros