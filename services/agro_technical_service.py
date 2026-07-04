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
import time
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

# Modelo con capacidad de búsqueda web Y razonamiento. gpt-4.1 (no-razonado)
# solo resume snippets de búsqueda sin "entrar" a leer el documento encontrado,
# por eso citaba la fuente correcta pero no extraía cifras de adentro. Los
# modelos de razonamiento (familia gpt-5) sí pueden usar la acción open_page
# para leer el contenido real antes de responder. gpt-5.4-mini es la opción
# económica de esa familia con razonamiento habilitado.
MODELO_BUSQUEDA = "gpt-5.4-mini"
ESFUERZO_RAZONAMIENTO = "medium"  # "minimal"/"none" degradan la calidad de la búsqueda

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
    "apto_para_la_zona",
    "motivo_aptitud",
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
Eres un ingeniero agrónomo que recopila datos técnicos para un cálculo real.
NO debes recomendar, NO debes redactar explicaciones para agricultores,
NO debes calcular nada. Tu única salida es un JSON con parámetros crudos.

CULTIVO A INVESTIGAR: {cultivo}
UBICACIÓN: {municipio}, {departamento}, Colombia
{contexto}
{nota_correccion}

PASO 0 (CRÍTICO, responde primero esto mentalmente): ¿Es "{cultivo}" agronómicamente
apto para el clima y suelo de {municipio}, {departamento}? Considera altitud,
temperatura, precipitación y tipo de clima típico de esa zona (usa el contexto de
clima/suelo si te lo dieron arriba; si no, usa tu conocimiento general de la
región). Si el cultivo es claramente incompatible (ej. un cultivo tropical de
tierra caliente en un páramo frío, o un cultivo de clima frío en tierra caliente
húmeda), marca "apto_para_la_zona": false y explica por qué en "motivo_aptitud" —
en ese caso NO hace falta que investigues el resto de los campos con precisión,
pero igual debes llenarlos con algún valor técnicamente razonable (la app los
ignorará si no es apto). Si es razonablemente apto (la gran mayoría de casos),
usa "apto_para_la_zona": true.

PASO 1: Busca primero en fuentes técnicas (ICA, Agrosavia, Agronet, UPRA, FAO,
Fenalce, Fedepapa, Asohofrucol, universidades, SENA, gobernaciones/secretarías
de agricultura) los datos de este cultivo. Si una fuente da un rango, usa el
punto medio.

PASO 2: Para CUALQUIER campo numérico que no encuentres publicado explícitamente
en esas fuentes (muy común en cultivos de nicho/aromáticas/hortalizas gourmet,
que casi nunca tienen ficha técnica oficial), NO uses null: da tu MEJOR ESTIMACIÓN
TÉCNICA basada en tu conocimiento agronómico general para ese cultivo específico
(o, si de verdad no conoces ese cultivo puntual, para un cultivo comparable en
ciclo, densidad de siembra y manejo). Necesitamos SIEMPRE un número técnicamente
razonable en cada campo de costo/densidad/tiempo — la app depende de esto para
funcionar en cualquier cultivo y cualquier región de Colombia, incluso zonas o
cultivos poco documentados. Usa null ÚNICAMENTE en los dos campos de rendimiento
si el otro de los dos ya tiene valor (uno de los dos siempre debe tener dato).

PASO 3: En "fuentes_consultadas", incluye URLs reales completas (nunca marcadores
internos de citación como "turn0search0" — si no tienes una URL real que copiar
textualmente, no inventes una: en su lugar escribe la fuente en texto plano, ej.
"Estimación técnica basada en conocimiento agronómico general (sin ficha oficial
específica encontrada)").

Responde EXCLUSIVAMENTE con un JSON válido (sin texto adicional, sin marcadores
de código), con esta estructura EXACTA:

{{
  "apto_para_la_zona": true o false,
  "motivo_aptitud": "texto breve explicando el veredicto del PASO 0",
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
  "precio_venta_kg_cop": número,
  "epoca_siembra_recomendada": "texto",
  "calendario_riego": "texto",
  "calendario_fertilizacion": "texto",
  "plagas_comunes": [
    {{"nombre": "texto", "sintomas": "texto", "control": "texto", "epoca_riesgo": "texto"}}
  ],
  "beneficios_cultivo": ["texto", "texto"],
  "fuentes_consultadas": ["url1 real, o texto explicando que fue estimación técnica"]
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


def _limpiar_fuentes(parametros):
    """
    El modelo a veces copia marcadores internos de citación de la Responses
    API (ej. 'turn0search0') en vez de una URL real. Los filtramos para no
    hacerle creer al usuario que eso es una fuente verificable.
    """
    fuentes = parametros.get("fuentes_consultadas")
    if not isinstance(fuentes, list):
        return parametros

    patron_marcador = re.compile(r"^turn\d+search\d+$", re.IGNORECASE)
    limpias = [f for f in fuentes if isinstance(f, str) and not patron_marcador.match(f.strip())]
    parametros["fuentes_consultadas"] = limpias
    return parametros


def _post_a_responses_api(payload, timeout, max_reintentos_429=2):
    """
    POST a la Responses API con reintento SOLO para 429 (rate limit de
    OpenAI) — ese error llega casi instantáneo, así que reintentar es
    barato en tiempo. Otros errores (timeout, red, 4xx/5xx distintos)
    probablemente no se arreglan reintentando, así que fallan de una vez
    y el llamador decide (retry con corrección, o fallback genérico).

    Retorna (data: dict, error: str|None).
    """
    intentos = 0
    while True:
        intentos += 1
        try:
            resp = requests.post(
                OPENAI_RESPONSES_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                },
                json=payload,
                timeout=timeout,
            )
        except requests.exceptions.Timeout:
            return None, "Timeout esperando respuesta del modelo de búsqueda"
        except requests.exceptions.RequestException as e:
            return None, f"Error de conexión: {e}"

        if resp.status_code == 429:
            if intentos <= max_reintentos_429:
                espera = 8 * intentos  # 8s, 16s
                print(f"[agro_technical_service] 429 (rate limit) recibido, reintentando en {espera}s (intento {intentos})")
                time.sleep(espera)
                continue
            return None, "429 Too Many Requests (límite de tasa de OpenAI, incluso tras reintentos)"

        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            return None, f"Error HTTP {resp.status_code}: {e}"

        return resp.json(), None


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
        "reasoning": {"effort": ESFUERZO_RAZONAMIENTO},
        "tools": [
            {
                "type": "web_search",
                "filters": {"allowed_domains": DOMINIOS_CONFIABLES},
            }
        ],
        "tool_choice": "auto",
        "input": prompt,
    }

    data, error = _post_a_responses_api(payload, timeout=150)
    if error:
        return {"error": f"Error consultando el modelo de búsqueda: {error}"}

    texto = _extraer_texto_respuesta(data)
    parametros = _extraer_json(texto)

    if parametros is None:
        return {"error": "La IA de búsqueda no devolvió un JSON válido", "raw": texto[:500]}

    faltantes = [c for c in CAMPOS_REQUERIDOS if c not in parametros]
    if faltantes:
        return {"error": f"Faltan campos en la respuesta de la IA: {faltantes}", "parcial": parametros}

    return _limpiar_fuentes(parametros)


# -----------------------------------------------------------------
# CANDIDATOS DE CULTIVO (para la pantalla de "Opciones de siembra")
# -----------------------------------------------------------------
# Mismo principio que obtener_parametros_tecnicos, pero en vez de investigar
# UN cultivo ya elegido, le pide a la IA que PROPONGA varios cultivos
# apropiados para la zona (clima/suelo) y devuelva los mismos parámetros
# técnicos crudos de cada uno, para que app.py calcule la rentabilidad real
# de cada candidato en Python (calculo_agricola.py) y solo se muestren al
# agricultor los que efectivamente dan positivo con su presupuesto y área.
# Así se evita repetir siempre "los mismos 2 cultivos": la propuesta inicial
# también queda anclada a datos de búsqueda + matemáticas, no a texto libre.

CAMPOS_REQUERIDOS_CANDIDATO = ["nombre_cultivo"] + CAMPOS_REQUERIDOS


def _construir_prompt_candidatos(departamento, municipio, contexto_clima_suelo, tipo_terreno, correccion=None):
    contexto = f"\n\nCONTEXTO DE CLIMA Y SUELO YA MEDIDO EN LA ZONA:\n{contexto_clima_suelo}" if contexto_clima_suelo else ""
    terreno = f"\nTIPO DE TERRENO: {tipo_terreno}" if tipo_terreno else ""
    nota_correccion = ""
    if correccion:
        nota_correccion = f"""
IMPORTANTE - CORRECCIÓN REQUERIDA:
En tu respuesta anterior, estos candidatos tenían valores fuera de rango o no
verificables:
{correccion}
Reemplázalos por otros cultivos distintos, o corrige sus cifras con datos reales.
"""

    return f"""
Eres un asistente técnico que SOLO recopila datos agronómicos verificables mediante
búsqueda web. NO debes redactar explicaciones para agricultores. Tu única salida
es un JSON con una lista de cultivos candidatos y sus parámetros crudos.

UBICACIÓN: {municipio}, {departamento}, Colombia
{contexto}{terreno}
{nota_correccion}

Propón entre 6 y 8 cultivos DIFERENTES ENTRE SÍ que sean agronómicamente
apropiados para el clima y suelo de esta zona (no solo los más obvios/genéricos:
incluye al menos 2 opciones menos comunes pero viables, como hortalizas
gourmet, aromáticas o frutas andinas, si el clima las permite).

Para cada uno: PASO 1, busca en fuentes técnicas (ICA, Agrosavia, Agronet, UPRA,
FAO, Fenalce, Fedepapa, Asohofrucol, universidades, SENA, gobernaciones/secretarías
de agricultura) los datos necesarios. PASO 2, para cualquier campo numérico que
no encuentres publicado explícitamente (común en cultivos de nicho), da tu MEJOR
ESTIMACIÓN TÉCNICA basada en conocimiento agronómico general para ese cultivo o
uno comparable — NO uses null en campos de costo/densidad/tiempo, la app necesita
un número técnicamente razonable siempre. Usa null solo en uno de los dos campos
de rendimiento si el otro ya tiene valor. PASO 3, en "fuentes_consultadas" pon
URLs reales completas — nunca marcadores internos de citación como "turn0search0";
si no tienes URL real, escribe en texto plano que fue una estimación técnica.

Responde EXCLUSIVAMENTE con un JSON válido (sin texto adicional, sin marcadores
de código), con esta estructura EXACTA:

{{
  "candidatos": [
    {{
      "nombre_cultivo": "texto",
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
      "precio_venta_kg_cop": número,
      "epoca_siembra_recomendada": "texto",
      "calendario_riego": "texto",
      "calendario_fertilizacion": "texto",
      "plagas_comunes": [
        {{"nombre": "texto", "sintomas": "texto", "control": "texto", "epoca_riesgo": "texto"}}
      ],
      "beneficios_cultivo": ["texto", "texto"],
      "fuentes_consultadas": ["url1 real, o texto explicando que fue estimación técnica"]
    }}
  ]
}}
"""


def obtener_candidatos_cultivo(departamento, municipio, contexto_clima_suelo=None, tipo_terreno=None, correccion=None):
    """
    Devuelve {"candidatos": [dict, dict, ...]} o {"error": "..."}.
    Cada dict tiene el mismo esquema que obtener_parametros_tecnicos, más
    "nombre_cultivo". No calcula ni filtra por viabilidad: eso lo hace
    app.py con calculo_agricola.py para cada candidato.
    """
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY no configurada en el backend"}

    prompt = _construir_prompt_candidatos(departamento, municipio, contexto_clima_suelo, tipo_terreno, correccion)

    payload = {
        "model": MODELO_BUSQUEDA,
        "reasoning": {"effort": ESFUERZO_RAZONAMIENTO},
        "tools": [
            {
                "type": "web_search",
                "filters": {"allowed_domains": DOMINIOS_CONFIABLES},
            }
        ],
        "tool_choice": "auto",
        "input": prompt,
    }

    data, error = _post_a_responses_api(payload, timeout=280, max_reintentos_429=1)
    if error:
        return {"error": f"Error consultando el modelo de búsqueda: {error}"}

    texto = _extraer_texto_respuesta(data)
    resultado = _extraer_json(texto)

    if resultado is None or "candidatos" not in resultado or not isinstance(resultado["candidatos"], list):
        return {"error": "La IA de búsqueda no devolvió una lista de candidatos válida", "raw": texto[:500]}

    resultado["candidatos"] = [_limpiar_fuentes(c) for c in resultado["candidatos"] if isinstance(c, dict)]
    return resultado