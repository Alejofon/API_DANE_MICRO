# services/tabla_referencia_cultivos.py
"""
TABLA CURADA DE CULTIVOS (fuente estática, gratis, instantánea, sin IA).

Este es el primer lugar donde el backend busca los parámetros técnicos de un
cultivo. Si el cultivo está aquí, NO se llama a la IA de búsqueda (rápido,
sin costo, sin alucinaciones). Solo si el cultivo NO está aquí se recurre a
agro_technical_service (IA + web_search), y ese resultado se cachea en
Postgres (cache_tecnico_service) para no repetir la llamada.

HONESTIDAD DE FUENTES (importante para la sustentación del proyecto):
cada cultivo declara en "fuentes_consultadas" de dónde salen sus cifras.
- "Ficha oficial Agronet/MADR-CCI ..." = costos/rendimiento/jornales tomados
  de una ficha de costos oficial publicada (URL en la lista).
- "Referencia agronómica general" = valor de manejo típico del cultivo en
  Colombia (densidad de siembra, rango de altitud/temperatura), no una cifra
  de una ficha oficial puntual. Se marca así para no presentarlo como dato
  citado cuando no lo es.

El precio de venta (precio_venta_kg_cop) NO se pone aquí a propósito: el
backend lo toma en vivo de la tabla dane_normalizado (SIPSA/DANE, actualizada
a diario), que es más confiable y siempre vigente.

Estructura de cada entrada: idéntica al dict que devuelve
agro_technical_service.obtener_parametros_tecnicos, más rango_altitud_msnm y
rango_temperatura_c para verificar aptitud climática sin IA.

Para AMPLIAR la tabla: agrega una entrada nueva siguiendo el mismo formato.
La clave es el nombre en minúsculas y sin tildes (se normaliza al buscar).
"""

import unicodedata


def _normalizar(nombre):
    """minúsculas, sin tildes, sin espacios extra — para casar nombres del usuario/IA."""
    if not nombre:
        return ""
    texto = unicodedata.normalize("NFKD", str(nombre))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower()


# ---------------------------------------------------------------------------
# GRUPO A — Cultivos con FICHA OFICIAL Agronet/MADR-CCI (datos verificados).
# Investigados y citados uno por uno. Costos, jornales y rendimiento salen de
# las fichas de costos de producción publicadas en agronet.gov.co / upra.gov.co.
# ---------------------------------------------------------------------------

TABLA_CULTIVOS = {
    "tomate": {
        "nombre_cultivo": "Tomate",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 1.2,
        "distancia_entre_plantas_m": 0.4,
        "costo_semilla_o_plantula_unidad_cop": 100,
        "costo_preparacion_terreno_por_ha_cop": 733260,
        "costo_fertilizantes_por_ha_cop": 3319012,
        "costo_agroquimicos_control_plagas_por_ha_cop": 641809,
        "jornales_necesarios_por_ha_ciclo": 84,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 106312,
        "ciclo_productivo_meses": 6,
        "rango_altitud_msnm": [0, 2200],
        "rango_temperatura_c": [16, 30],
        "epoca_siembra_recomendada": "Se adapta a siembras escalonadas; en zona fría de altiplano preferir épocas de menor riesgo de heladas.",
        "calendario_riego": "Riego frecuente y constante, especialmente en floración y llenado de fruto.",
        "calendario_fertilizacion": "Fertilización fraccionada según etapa (establecimiento, floración, fructificación).",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Alta demanda en el mercado", "Rendimiento elevado por hectárea"],
        "fuentes_consultadas": [
            "Ficha oficial Agronet/MADR-CCI, Tomate mediano 0.25 ha: https://agronet.gov.co/sites/default/files/2025-11/EC%20Tomate-mediano%20(0.25ha)_0.pdf",
            "Distancias de siembra y rango altitud/temperatura: referencia agronómica general",
        ],
    },
    "maiz": {
        "nombre_cultivo": "Maíz",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.8,
        "distancia_entre_plantas_m": 0.2,
        "costo_semilla_o_plantula_unidad_cop": 150,
        "costo_preparacion_terreno_por_ha_cop": 306667,
        "costo_fertilizantes_por_ha_cop": 279477,
        "costo_agroquimicos_control_plagas_por_ha_cop": 201558,
        "jornales_necesarios_por_ha_ciclo": 29,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 5708,
        "ciclo_productivo_meses": 4,
        "rango_altitud_msnm": [0, 2600],
        "rango_temperatura_c": [12, 30],
        "epoca_siembra_recomendada": "Inicio de temporada de lluvias.",
        "calendario_riego": "Sensible a déficit hídrico en floración; complementar riego si la lluvia es insuficiente.",
        "calendario_fertilizacion": "Fertilización nitrogenada fraccionada (siembra y etapa vegetativa).",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Cultivo básico de amplia demanda", "Manejo mecanizable"],
        "fuentes_consultadas": [
            "Ficha oficial Agronet/MADR-CCI, Maíz amarillo mecanizado grande: https://agronet.gov.co/sites/default/files/2025-11/EC%20Ma%C3%ADz%20amarillo%20mecanizado-grande.pdf",
            "Variedad Agrosavia V-121 (densidad de siembra): https://www.agrosavia.co/productos-y-servicios/oferta-tecnol%C3%B3gica",
            "Distancia entre plantas, costo semilla unitaria y rango altitud/temperatura: referencia agronómica general",
        ],
    },
    "frijol": {
        "nombre_cultivo": "Fríjol",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.5,
        "distancia_entre_plantas_m": 0.15,
        "costo_semilla_o_plantula_unidad_cop": 80,
        "costo_preparacion_terreno_por_ha_cop": 566650,
        "costo_fertilizantes_por_ha_cop": 861205,
        "costo_agroquimicos_control_plagas_por_ha_cop": 264350,
        "jornales_necesarios_por_ha_ciclo": 55,
        "valor_jornal_cop": 39286,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 1803,
        "ciclo_productivo_meses": 3.5,
        "rango_altitud_msnm": [0, 2800],
        "rango_temperatura_c": [12, 28],
        "epoca_siembra_recomendada": "Inicio de lluvias; evitar exceso de humedad en cosecha.",
        "calendario_riego": "Riego moderado; sensible tanto a sequía como a encharcamiento.",
        "calendario_fertilizacion": "Fertilización de fondo; leguminosa con aporte propio de nitrógeno.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Leguminosa que mejora el suelo", "Ciclo corto"],
        "fuentes_consultadas": [
            "Boletín oficial UPRA 2022, Costos de producción de fríjol (promedio 7 regiones): https://upra.gov.co/sites/default/files/2025-04/BOLETIN_FRIJOL_S1.pdf",
            "Trazado y siembra de fríjol (Agrosavia): https://repository.agrosavia.co/",
            "NOTA: alta dispersión regional (rendimiento 0.74-3.93 t/ha); el promedio nacional puede no representar bien una región puntual.",
        ],
    },
    "cacao": {
        "nombre_cultivo": "Cacao",
        "categoria_cultivo": "arboreo_frutal",
        "distancia_entre_surcos_m": 3.0,
        "distancia_entre_plantas_m": 3.0,
        "costo_semilla_o_plantula_unidad_cop": 2000,
        "costo_preparacion_terreno_por_ha_cop": 70993,
        "costo_fertilizantes_por_ha_cop": 702740,
        "costo_agroquimicos_control_plagas_por_ha_cop": 50000,
        "jornales_necesarios_por_ha_ciclo": 66,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 880,
        "ciclo_productivo_meses": 30,
        "rango_altitud_msnm": [0, 1400],
        "rango_temperatura_c": [21, 32],
        "epoca_siembra_recomendada": "Establecer al inicio de lluvias; requiere sombrío en establecimiento.",
        "calendario_riego": "Sensible a sequía prolongada; mantener humedad en establecimiento.",
        "calendario_fertilizacion": "Fertilización según análisis de suelo, creciente con la edad del árbol.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Cultivo permanente de largo plazo", "Mercado de exportación"],
        "fuentes_consultadas": [
            "Ficha oficial Agronet/MADR-CCI, Cacao pequeño <5 ha: https://agronet.gov.co/sites/default/files/2025-11/EC%20Cacao-peque%C3%B1o.pdf",
            "Rendimiento de Año 3 (primer año con cosecha significativa). Densidad 3x3 m, altitud/temperatura: referencia agronómica general",
        ],
    },
    "platano": {
        "nombre_cultivo": "Plátano",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 3.0,
        "distancia_entre_plantas_m": 2.5,
        "costo_semilla_o_plantula_unidad_cop": 500,
        "costo_preparacion_terreno_por_ha_cop": 352721,
        "costo_fertilizantes_por_ha_cop": 611297,
        "costo_agroquimicos_control_plagas_por_ha_cop": 184218,
        "jornales_necesarios_por_ha_ciclo": 41,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 9333,
        "ciclo_productivo_meses": 12,
        "rango_altitud_msnm": [0, 2000],
        "rango_temperatura_c": [18, 30],
        "epoca_siembra_recomendada": "Inicio de lluvias; requiere buen drenaje.",
        "calendario_riego": "Alta demanda de agua constante.",
        "calendario_fertilizacion": "Fertilización rica en potasio, fraccionada durante el ciclo.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Producción escalonada continua", "Alta demanda local"],
        "fuentes_consultadas": [
            "Ficha oficial Agronet/MADR-CCI, Plátano mediano: https://agronet.gov.co/sites/default/files/2025-11/EC%20Platano-mediano.pdf",
            "Ciclo anual de mantenimiento (Año 2). Densidad de siembra, altitud/temperatura: referencia agronómica general",
        ],
    },
    "cafe": {
        "nombre_cultivo": "Café",
        "categoria_cultivo": "arboreo_frutal",
        "distancia_entre_surcos_m": 1.5,
        "distancia_entre_plantas_m": 1.0,
        "costo_semilla_o_plantula_unidad_cop": 200,
        "costo_preparacion_terreno_por_ha_cop": 110000,
        "costo_fertilizantes_por_ha_cop": 1717324,
        "costo_agroquimicos_control_plagas_por_ha_cop": 49684,
        "jornales_necesarios_por_ha_ciclo": 482,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 4201,
        "ciclo_productivo_meses": 36,
        "rango_altitud_msnm": [1200, 2000],
        "rango_temperatura_c": [17, 23],
        "epoca_siembra_recomendada": "Establecer al inicio de lluvias; zona cafetera de ladera.",
        "calendario_riego": "Generalmente de secano en zona cafetera; complementar en veranos intensos.",
        "calendario_fertilizacion": "Fertilización intensiva fraccionada (hasta 3-4 veces al año en producción).",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Mercado de exportación consolidado", "Cultivo emblemático con apoyo gremial"],
        "fuentes_consultadas": [
            "Ficha oficial Agronet/MADR-CCI, Café tecnificado grande: https://agronet.gov.co/sites/default/files/2025-11/EC%20Caf%C3%A9%20tecnificado-grande_0.pdf",
            "Jornales y rendimiento de Año 3 (primer año productivo consolidado). Densidad de siembra: referencia agronómica general",
        ],
    },

    # -----------------------------------------------------------------------
    # GRUPO B — Cultivos de CLIMA FRÍO del altiplano cundiboyacense
    # (zona de pruebas: Villapinzón, Chocontá, cercanías de Tocancipá,
    # ~2500-3100 msnm). Densidades de siembra, ciclos, rangos de altitud y
    # temperatura son referencia agronómica general para clima frío andino;
    # los costos son órdenes de magnitud coherentes con estructuras de costos
    # de hortalizas/tubérculos de clima frío en Colombia. Se marcan como
    # referencia para no presentarlos como ficha oficial puntual. Refinar con
    # una ficha específica cuando se disponga (mejora futura, no bloquea la
    # demo: el precio de venta siempre viene del DANE real).
    # -----------------------------------------------------------------------
    "papa": {
        "nombre_cultivo": "Papa",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 1.0,
        "distancia_entre_plantas_m": 0.3,
        "costo_semilla_o_plantula_unidad_cop": 500,
        "costo_preparacion_terreno_por_ha_cop": 2000000,
        "costo_fertilizantes_por_ha_cop": 8000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 6000000,
        "jornales_necesarios_por_ha_ciclo": 120,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 22000,
        "ciclo_productivo_meses": 5,
        "rango_altitud_msnm": [2000, 3200],
        "rango_temperatura_c": [6, 18],
        "epoca_siembra_recomendada": "Dos épocas típicas en el altiplano (año grande y traviesa), asociadas al régimen de lluvias.",
        "calendario_riego": "Generalmente de secano en clima frío; complementar en veranos fuertes.",
        "calendario_fertilizacion": "Alta demanda de fertilización (siembra y aporque); cultivo exigente en nutrientes.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Cultivo tradicional del altiplano", "Alta demanda nacional constante"],
        "fuentes_consultadas": [
            "Referencia agronómica general para papa de clima frío (altiplano cundiboyacense). "
            "Los costos de insumos de la papa son altos y volátiles (Fedepapa reportó ~$15.6M/ha en 2018 y ~$35M/ha en 2024); "
            "estas cifras son un punto de partida a refinar con la ficha vigente.",
        ],
    },
    "papa criolla": {
        "nombre_cultivo": "Papa criolla",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 1.0,
        "distancia_entre_plantas_m": 0.3,
        "costo_semilla_o_plantula_unidad_cop": 500,
        "costo_preparacion_terreno_por_ha_cop": 2000000,
        "costo_fertilizantes_por_ha_cop": 7000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 5000000,
        "jornales_necesarios_por_ha_ciclo": 110,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 12000,
        "ciclo_productivo_meses": 4,
        "rango_altitud_msnm": [2000, 3000],
        "rango_temperatura_c": [8, 18],
        "epoca_siembra_recomendada": "Asociada al régimen de lluvias del altiplano; ciclo más corto que la papa común.",
        "calendario_riego": "De secano en clima frío; complementar en veranos.",
        "calendario_fertilizacion": "Fertilización en siembra y aporque.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Ciclo más corto que la papa común", "Buen precio de mercado"],
        "fuentes_consultadas": [
            "Referencia agronómica general para papa criolla de clima frío (altiplano). Rendimiento típicamente menor que la papa común, ciclo más corto.",
        ],
    },
    "arveja": {
        "nombre_cultivo": "Arveja",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.9,
        "distancia_entre_plantas_m": 0.1,
        "costo_semilla_o_plantula_unidad_cop": 60,
        "costo_preparacion_terreno_por_ha_cop": 1200000,
        "costo_fertilizantes_por_ha_cop": 2000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1500000,
        "jornales_necesarios_por_ha_ciclo": 90,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 4000,
        "ciclo_productivo_meses": 4,
        "rango_altitud_msnm": [1800, 2800],
        "rango_temperatura_c": [10, 18],
        "epoca_siembra_recomendada": "Clima frío moderado; sensible a exceso de lluvia en floración.",
        "calendario_riego": "Riego moderado; leguminosa sensible a encharcamiento.",
        "calendario_fertilizacion": "Baja demanda de nitrógeno (fija N); fósforo en siembra.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Leguminosa que mejora el suelo", "Buen precio en verde"],
        "fuentes_consultadas": [
            "Referencia agronómica general para arveja de clima frío andino (a menudo tutorada).",
        ],
    },
    "zanahoria": {
        "nombre_cultivo": "Zanahoria",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.3,
        "distancia_entre_plantas_m": 0.07,
        "costo_semilla_o_plantula_unidad_cop": 10,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 2500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1500000,
        "jornales_necesarios_por_ha_ciclo": 130,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 30000,
        "ciclo_productivo_meses": 4,
        "rango_altitud_msnm": [1800, 3000],
        "rango_temperatura_c": [8, 18],
        "epoca_siembra_recomendada": "Siembra directa; clima frío del altiplano.",
        "calendario_riego": "Riego constante para raíz uniforme; evitar déficit.",
        "calendario_fertilizacion": "Fertilización fosfórica y potásica; moderar nitrógeno.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Alto rendimiento por hectárea", "Demanda estable"],
        "fuentes_consultadas": [
            "Referencia agronómica general para zanahoria de clima frío (siembra directa de alta densidad).",
        ],
    },
    "cebolla larga": {
        "nombre_cultivo": "Cebolla larga",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.5,
        "distancia_entre_plantas_m": 0.15,
        "costo_semilla_o_plantula_unidad_cop": 40,
        "costo_preparacion_terreno_por_ha_cop": 1800000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1800000,
        "jornales_necesarios_por_ha_ciclo": 150,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 35000,
        "ciclo_productivo_meses": 5,
        "rango_altitud_msnm": [1800, 2800],
        "rango_temperatura_c": [10, 20],
        "epoca_siembra_recomendada": "Trasplante de macolla; clima frío moderado.",
        "calendario_riego": "Riego frecuente; sensible a estrés hídrico.",
        "calendario_fertilizacion": "Alta demanda de nitrógeno para desarrollo foliar.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Cortes escalonados posibles", "Demanda continua"],
        "fuentes_consultadas": [
            "Referencia agronómica general para cebolla larga (de rama) de clima frío andino.",
        ],
    },
    "cebolla cabezona": {
        "nombre_cultivo": "Cebolla cabezona",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.4,
        "distancia_entre_plantas_m": 0.1,
        "costo_semilla_o_plantula_unidad_cop": 20,
        "costo_preparacion_terreno_por_ha_cop": 1800000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2000000,
        "jornales_necesarios_por_ha_ciclo": 140,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 30000,
        "ciclo_productivo_meses": 5,
        "rango_altitud_msnm": [1500, 2800],
        "rango_temperatura_c": [10, 22],
        "epoca_siembra_recomendada": "Trasplante de plántula; requiere buen drenaje.",
        "calendario_riego": "Riego regular, reducir cerca de la cosecha (curado del bulbo).",
        "calendario_fertilizacion": "Nitrógeno y azufre; moderar N al final del ciclo.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Bulbo almacenable", "Demanda estable"],
        "fuentes_consultadas": [
            "Referencia agronómica general para cebolla de bulbo de clima frío andino.",
        ],
    },
    "lechuga": {
        "nombre_cultivo": "Lechuga",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.3,
        "distancia_entre_plantas_m": 0.3,
        "costo_semilla_o_plantula_unidad_cop": 80,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 2000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1000000,
        "jornales_necesarios_por_ha_ciclo": 100,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": 0.35,
        "rendimiento_estimado_kg_por_ha": None,
        "ciclo_productivo_meses": 2.5,
        "rango_altitud_msnm": [1800, 3000],
        "rango_temperatura_c": [8, 18],
        "epoca_siembra_recomendada": "Trasplante; ciclo muy corto, siembras escalonadas.",
        "calendario_riego": "Riego frecuente y ligero; cultivo de hoja sensible a sequía.",
        "calendario_fertilizacion": "Nitrógeno para desarrollo foliar rápido.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Ciclo muy corto (rotación rápida)", "Demanda urbana constante"],
        "fuentes_consultadas": [
            "Referencia agronómica general para lechuga de clima frío (ciclo corto, trasplante).",
        ],
    },
    "repollo": {
        "nombre_cultivo": "Repollo",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.6,
        "distancia_entre_plantas_m": 0.4,
        "costo_semilla_o_plantula_unidad_cop": 90,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 2500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1500000,
        "jornales_necesarios_por_ha_ciclo": 110,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": 1.5,
        "rendimiento_estimado_kg_por_ha": None,
        "ciclo_productivo_meses": 3.5,
        "rango_altitud_msnm": [1800, 3000],
        "rango_temperatura_c": [8, 18],
        "epoca_siembra_recomendada": "Trasplante; buena adaptación a clima frío.",
        "calendario_riego": "Riego regular; sensible a déficit en formación de cabeza.",
        "calendario_fertilizacion": "Alta demanda de nitrógeno.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Rústico y adaptado al frío", "Cabeza almacenable"],
        "fuentes_consultadas": [
            "Referencia agronómica general para repollo de clima frío andino.",
        ],
    },
    "brocoli": {
        "nombre_cultivo": "Brócoli",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.7,
        "distancia_entre_plantas_m": 0.4,
        "costo_semilla_o_plantula_unidad_cop": 120,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 2800000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1600000,
        "jornales_necesarios_por_ha_ciclo": 115,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": 0.5,
        "rendimiento_estimado_kg_por_ha": None,
        "ciclo_productivo_meses": 3.5,
        "rango_altitud_msnm": [2000, 3000],
        "rango_temperatura_c": [8, 18],
        "epoca_siembra_recomendada": "Trasplante; clima frío del altiplano.",
        "calendario_riego": "Riego regular y constante.",
        "calendario_fertilizacion": "Alta demanda de nitrógeno y boro.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Buen precio de mercado", "Adaptado a clima frío"],
        "fuentes_consultadas": [
            "Referencia agronómica general para brócoli de clima frío andino.",
        ],
    },
    "haba": {
        "nombre_cultivo": "Haba",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.8,
        "distancia_entre_plantas_m": 0.3,
        "costo_semilla_o_plantula_unidad_cop": 150,
        "costo_preparacion_terreno_por_ha_cop": 1200000,
        "costo_fertilizantes_por_ha_cop": 1500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 800000,
        "jornales_necesarios_por_ha_ciclo": 80,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 8000,
        "ciclo_productivo_meses": 5,
        "rango_altitud_msnm": [2200, 3200],
        "rango_temperatura_c": [6, 16],
        "epoca_siembra_recomendada": "Clima frío alto; tolera bajas temperaturas.",
        "calendario_riego": "Riego moderado; leguminosa rústica.",
        "calendario_fertilizacion": "Baja demanda de nitrógeno (fija N).",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Leguminosa rústica de clima frío alto", "Mejora el suelo"],
        "fuentes_consultadas": [
            "Referencia agronómica general para haba de clima frío alto (páramo bajo/altiplano).",
        ],
    },
    "ajo": {
        "nombre_cultivo": "Ajo",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.3,
        "distancia_entre_plantas_m": 0.1,
        "costo_semilla_o_plantula_unidad_cop": 150,
        "costo_preparacion_terreno_por_ha_cop": 1800000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1800000,
        "jornales_necesarios_por_ha_ciclo": 160,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 8000,
        "ciclo_productivo_meses": 6,
        "rango_altitud_msnm": [2000, 3000],
        "rango_temperatura_c": [8, 18],
        "epoca_siembra_recomendada": "Siembra de bulbillos; clima frío seco.",
        "calendario_riego": "Riego moderado; reducir cerca de la cosecha.",
        "calendario_fertilizacion": "Nitrógeno y azufre; fraccionado.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Bulbo almacenable de buen precio", "Adaptado a clima frío"],
        "fuentes_consultadas": [
            "Referencia agronómica general para ajo de clima frío andino.",
        ],
    },

    # -----------------------------------------------------------------------
    # GRUPO C — FRUTALES DE VALOR AGREGADO con FINAGRO Marco de Referencia
    # Agroeconómico (MRA). El MRA aporta densidad de siembra, clima, ciclo,
    # rendimiento y precios REALES de referencia. Los costos del MRA vienen
    # como flujo multi-anual; aquí se aproximan a componentes por hectárea
    # coherentes con el total del MRA (marcado como "derivado del MRA"). El
    # precio de venta lo pone el DANE en vivo, no estos números.
    # -----------------------------------------------------------------------
    "lulo": {
        "nombre_cultivo": "Lulo",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 3.0,
        "distancia_entre_plantas_m": 2.5,
        "costo_semilla_o_plantula_unidad_cop": 1500,
        "costo_preparacion_terreno_por_ha_cop": 600000,
        "costo_fertilizantes_por_ha_cop": 3200000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1600000,
        "jornales_necesarios_por_ha_ciclo": 480,
        "valor_jornal_cop": 35000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 30000,
        "ciclo_productivo_meses": 36,
        "rango_altitud_msnm": [1500, 2300],
        "rango_temperatura_c": [14, 22],
        "epoca_siembra_recomendada": "Trasplante de plántula; clima templado de ladera con sombrío parcial.",
        "calendario_riego": "Requiere humedad constante; sensible a sequía prolongada.",
        "calendario_fertilizacion": "Alta demanda de fertilización edáfica y enmiendas durante todo el ciclo.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Fruta andina de alto valor y demanda creciente", "Cosecha escalonada por ~3 años"],
        "fuentes_consultadas": [
            "FINAGRO, Marco de Referencia Agroeconómico Lulo (Antioquia, 2017): densidad 1.333 plantas/ha (2,5×3 m), altitud 1.740 msnm, temp media 19°C, rendimiento ~30.375 kg/ha/ciclo (3 años), jornal $35.000. Desglose de costos por ha DERIVADO del total del MRA. https://www.finagro.com.co/sites/default/files/2022-05/lulo.pdf",
        ],
    },
    "gulupa": {
        "nombre_cultivo": "Gulupa",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 4.0,
        "distancia_entre_plantas_m": 2.5,
        "costo_semilla_o_plantula_unidad_cop": 2000,
        "costo_preparacion_terreno_por_ha_cop": 700000,
        "costo_fertilizantes_por_ha_cop": 4000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2500000,
        "jornales_necesarios_por_ha_ciclo": 500,
        "valor_jornal_cop": 30000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 28000,
        "ciclo_productivo_meses": 48,
        "rango_altitud_msnm": [1600, 2400],
        "rango_temperatura_c": [15, 24],
        "epoca_siembra_recomendada": "Trasplante con sistema de tutorado (espaldera); clima frío moderado.",
        "calendario_riego": "Humedad constante; buen drenaje obligatorio.",
        "calendario_fertilizacion": "Fertilización edáfica y foliar fraccionada.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Fruta de exportación de MUY alto valor ($ premium)", "Nicho con demanda internacional"],
        "fuentes_consultadas": [
            "FINAGRO, Marco de Referencia Agroeconómico Gulupa (2017): densidad 1.000 plantas/ha (4×2,5 m), altitud 2.000 msnm, temp 16-24°C, rendimiento ~28.069 kg/ha/ciclo (4 años), precio 1ra calidad ~$4.650/kg, jornal $30.000. Desglose de costos por ha DERIVADO del total del MRA. https://www.finagro.com.co/sites/default/files/2022-05/gulupa.pdf",
        ],
    },
    "pina": {
        "nombre_cultivo": "Piña",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 0.8,
        "distancia_entre_plantas_m": 0.2,
        "costo_semilla_o_plantula_unidad_cop": 250,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 6000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2500000,
        "jornales_necesarios_por_ha_ciclo": 300,
        "valor_jornal_cop": 35000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 78000,
        "ciclo_productivo_meses": 18,
        "rango_altitud_msnm": [0, 1200],
        "rango_temperatura_c": [20, 32],
        "epoca_siembra_recomendada": "Siembra de colinos de alta densidad; tierra caliente.",
        "calendario_riego": "Tolera sequía; riego complementario mejora tamaño de fruto.",
        "calendario_fertilizacion": "Alta demanda de fertilización (edáfica y foliar).",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Alto rendimiento por hectárea", "Fruta de amplia demanda nacional y agroindustrial"],
        "fuentes_consultadas": [
            "FINAGRO, Marco de Referencia Agroeconómico Piña perolera (2018): densidad 65.625 plantas/ha (0,2×0,8 m), altitud 250-550 msnm, temp 20-30°C, rendimiento ~78.000 kg/ha/ciclo, jornal $35.000. Desglose de costos por ha DERIVADO del total del MRA. https://www.finagro.com.co/sites/default/files/2022-05/pina_perolera.pdf",
        ],
    },
    "aguacate": {
        "nombre_cultivo": "Aguacate Hass",
        "categoria_cultivo": "arboreo_frutal",
        "distancia_entre_surcos_m": 7.0,
        "distancia_entre_plantas_m": 6.0,
        "costo_semilla_o_plantula_unidad_cop": 9000,
        "costo_preparacion_terreno_por_ha_cop": 3000000,
        "costo_fertilizantes_por_ha_cop": 3500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2000000,
        "jornales_necesarios_por_ha_ciclo": 90,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 12000,
        "ciclo_productivo_meses": 36,
        "rango_altitud_msnm": [1800, 2600],
        "rango_temperatura_c": [12, 20],
        "epoca_siembra_recomendada": "Establecer al inicio de lluvias; clima frío moderado de ladera (Hass).",
        "calendario_riego": "Sensible a encharcamiento; riego en época seca.",
        "calendario_fertilizacion": "Fertilización creciente con la edad del árbol.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Cultivo de exportación consolidado", "Alta demanda internacional (Hass)"],
        "fuentes_consultadas": [
            "FINAGRO, Marco de Referencia Agroeconómico Aguacate Hass: densidad ~233 árboles/ha (7×6-7 m), altitud 2.300 msnm, temp media 16°C, precio 1ra calidad ~$1.600/kg. Rendimiento anualizado ~12.000 kg/ha en producción (el MRA reporta ~186.000 kg/ha para todo el ciclo multi-anual). Desglose de costos por ha DERIVADO del MRA. https://www.finagro.com.co/sites/default/files/2022-05/aguacate_hass.pdf",
        ],
    },
    "yuca": {
        "nombre_cultivo": "Yuca",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 1.0,
        "distancia_entre_plantas_m": 1.0,
        "costo_semilla_o_plantula_unidad_cop": 60,
        "costo_preparacion_terreno_por_ha_cop": 1200000,
        "costo_fertilizantes_por_ha_cop": 1500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 800000,
        "jornales_necesarios_por_ha_ciclo": 67,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 17000,
        "ciclo_productivo_meses": 10,
        "rango_altitud_msnm": [0, 1800],
        "rango_temperatura_c": [20, 32],
        "epoca_siembra_recomendada": "Siembra de estacas; rústica, tolera suelos pobres.",
        "calendario_riego": "Tolerante a sequía; poco exigente en riego.",
        "calendario_fertilizacion": "Baja demanda de fertilización comparada con hortalizas.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Rústica y de bajo insumo", "Seguridad alimentaria y mercado fresco/industrial"],
        "fuentes_consultadas": [
            "Agrosavia, estudio de costos de producción de yuca (8 regiones): ~67 jornales/ha promedio, densidad ~10.000 estacas/ha (1×1 m), productividad 12-23 t/ha. Costos actualizados a orden de magnitud vigente (el estudio base reporta pesos de 2003). https://www.agrosavia.co",
        ],
    },

    # -----------------------------------------------------------------------
    # GRUPO D — TIERRA CALIENTE / CARIBE (0-1000 msnm). Referencia agronómica
    # general de manejo típico en Colombia; el precio de venta lo pone el DANE.
    # -----------------------------------------------------------------------
    "mango": {
        "nombre_cultivo": "Mango",
        "categoria_cultivo": "arboreo_frutal",
        "distancia_entre_surcos_m": 8.0,
        "distancia_entre_plantas_m": 8.0,
        "costo_semilla_o_plantula_unidad_cop": 8000,
        "costo_preparacion_terreno_por_ha_cop": 2500000,
        "costo_fertilizantes_por_ha_cop": 2500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1500000,
        "jornales_necesarios_por_ha_ciclo": 70,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 15000,
        "ciclo_productivo_meses": 36,
        "rango_altitud_msnm": [0, 1200],
        "rango_temperatura_c": [22, 33],
        "epoca_siembra_recomendada": "Establecer al inicio de lluvias; tierra caliente con estación seca marcada.",
        "calendario_riego": "Riego en establecimiento; adulto tolera sequía (favorece floración).",
        "calendario_fertilizacion": "Fertilización según edad y etapa fenológica.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Árbol longevo de bajo mantenimiento en adultez", "Mercado fresco y agroindustrial"],
        "fuentes_consultadas": [
            "Referencia agronómica general para mango de tierra caliente en Colombia.",
        ],
    },
    "maracuya": {
        "nombre_cultivo": "Maracuyá",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 3.0,
        "distancia_entre_plantas_m": 3.0,
        "costo_semilla_o_plantula_unidad_cop": 800,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2000000,
        "jornales_necesarios_por_ha_ciclo": 200,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 25000,
        "ciclo_productivo_meses": 18,
        "rango_altitud_msnm": [0, 1400],
        "rango_temperatura_c": [21, 32],
        "epoca_siembra_recomendada": "Trasplante con tutorado (espaldera); tierra caliente/templada.",
        "calendario_riego": "Humedad constante; sensible a sequía en floración.",
        "calendario_fertilizacion": "Alta demanda de nutrientes durante producción.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Producción rápida (empieza ~6-8 meses)", "Alta demanda para jugo y exportación"],
        "fuentes_consultadas": [
            "Referencia agronómica general para maracuyá (Passiflora) de tierra caliente en Colombia.",
        ],
    },
    "papaya": {
        "nombre_cultivo": "Papaya",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 2.5,
        "distancia_entre_plantas_m": 2.0,
        "costo_semilla_o_plantula_unidad_cop": 500,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 3500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2500000,
        "jornales_necesarios_por_ha_ciclo": 150,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 45000,
        "ciclo_productivo_meses": 12,
        "rango_altitud_msnm": [0, 1200],
        "rango_temperatura_c": [21, 33],
        "epoca_siembra_recomendada": "Trasplante; tierra caliente, ciclo productivo relativamente corto.",
        "calendario_riego": "Riego frecuente; sensible a encharcamiento y a sequía.",
        "calendario_fertilizacion": "Alta demanda continua de nutrientes.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Producción temprana (~10-12 meses)", "Alto rendimiento por hectárea"],
        "fuentes_consultadas": [
            "Referencia agronómica general para papaya de tierra caliente en Colombia.",
        ],
    },
    "name": {
        "nombre_cultivo": "Ñame",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 1.0,
        "distancia_entre_plantas_m": 1.0,
        "costo_semilla_o_plantula_unidad_cop": 400,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 1500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 800000,
        "jornales_necesarios_por_ha_ciclo": 110,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 15000,
        "ciclo_productivo_meses": 9,
        "rango_altitud_msnm": [0, 1000],
        "rango_temperatura_c": [22, 32],
        "epoca_siembra_recomendada": "Siembra de semilla-tubérculo con tutorado; típico del Caribe colombiano.",
        "calendario_riego": "Ligado al régimen de lluvias; tolera condiciones del Caribe.",
        "calendario_fertilizacion": "Fertilización moderada.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Cultivo tradicional del Caribe con buen mercado", "Tubérculo almacenable"],
        "fuentes_consultadas": [
            "Referencia agronómica general para ñame (Dioscorea) del Caribe colombiano.",
        ],
    },
    "aji": {
        "nombre_cultivo": "Ají",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 1.0,
        "distancia_entre_plantas_m": 0.5,
        "costo_semilla_o_plantula_unidad_cop": 120,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2000000,
        "jornales_necesarios_por_ha_ciclo": 130,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 12000,
        "ciclo_productivo_meses": 6,
        "rango_altitud_msnm": [0, 1600],
        "rango_temperatura_c": [18, 32],
        "epoca_siembra_recomendada": "Trasplante; se adapta a tierra caliente y templada.",
        "calendario_riego": "Riego constante; sensible a estrés hídrico.",
        "calendario_fertilizacion": "Fertilización fraccionada rica en potasio.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Cultivo de exportación (ají tabasco/habanero)", "Cosecha escalonada de alto valor"],
        "fuentes_consultadas": [
            "Referencia agronómica general para ají (Capsicum) en Colombia.",
        ],
    },

    # -----------------------------------------------------------------------
    # GRUPO E — CLIMA TEMPLADO / CAFETERO (1000-2000 msnm). Referencia general.
    # -----------------------------------------------------------------------
    "tomate de arbol": {
        "nombre_cultivo": "Tomate de árbol",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 2.5,
        "distancia_entre_plantas_m": 2.0,
        "costo_semilla_o_plantula_unidad_cop": 1200,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2000000,
        "jornales_necesarios_por_ha_ciclo": 200,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 20000,
        "ciclo_productivo_meses": 18,
        "rango_altitud_msnm": [1600, 2600],
        "rango_temperatura_c": [13, 20],
        "epoca_siembra_recomendada": "Trasplante; clima frío moderado de ladera.",
        "calendario_riego": "Humedad constante; sensible a sequía.",
        "calendario_fertilizacion": "Fertilización fraccionada durante producción.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Fruta andina de buena demanda", "Producción escalonada por varios años"],
        "fuentes_consultadas": [
            "Referencia agronómica general para tomate de árbol de clima frío moderado andino.",
        ],
    },
    "mora": {
        "nombre_cultivo": "Mora",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 2.5,
        "distancia_entre_plantas_m": 2.0,
        "costo_semilla_o_plantula_unidad_cop": 1500,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1500000,
        "jornales_necesarios_por_ha_ciclo": 250,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 12000,
        "ciclo_productivo_meses": 18,
        "rango_altitud_msnm": [1800, 2800],
        "rango_temperatura_c": [11, 19],
        "epoca_siembra_recomendada": "Trasplante con tutorado; clima frío de ladera.",
        "calendario_riego": "Humedad constante; buen drenaje.",
        "calendario_fertilizacion": "Fertilización edáfica y foliar fraccionada.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Cosecha continua semanal por varios años", "Fruta de alta demanda para pulpa"],
        "fuentes_consultadas": [
            "Referencia agronómica general para mora de Castilla de clima frío andino.",
        ],
    },
    "granadilla": {
        "nombre_cultivo": "Granadilla",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 4.0,
        "distancia_entre_plantas_m": 3.0,
        "costo_semilla_o_plantula_unidad_cop": 1500,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 3500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2500000,
        "jornales_necesarios_por_ha_ciclo": 220,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 15000,
        "ciclo_productivo_meses": 24,
        "rango_altitud_msnm": [1600, 2400],
        "rango_temperatura_c": [14, 22],
        "epoca_siembra_recomendada": "Trasplante con emparrado/tutorado; clima templado-frío.",
        "calendario_riego": "Humedad constante; buen drenaje.",
        "calendario_fertilizacion": "Alta demanda durante producción.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Fruta de exportación de alto valor", "Nicho premium"],
        "fuentes_consultadas": [
            "Referencia agronómica general para granadilla de clima templado-frío andino.",
        ],
    },
    "fresa": {
        "nombre_cultivo": "Fresa",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.4,
        "distancia_entre_plantas_m": 0.3,
        "costo_semilla_o_plantula_unidad_cop": 400,
        "costo_preparacion_terreno_por_ha_cop": 4000000,
        "costo_fertilizantes_por_ha_cop": 6000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 4000000,
        "jornales_necesarios_por_ha_ciclo": 400,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 40000,
        "ciclo_productivo_meses": 12,
        "rango_altitud_msnm": [1800, 2800],
        "rango_temperatura_c": [10, 20],
        "epoca_siembra_recomendada": "Trasplante en camas con acolchado (plástico); clima frío.",
        "calendario_riego": "Riego por goteo frecuente.",
        "calendario_fertilizacion": "Fertirriego continuo; cultivo muy exigente.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Producción continua de alto valor por m²", "Demanda urbana fuerte"],
        "fuentes_consultadas": [
            "Referencia agronómica general para fresa de clima frío andino (alta inversión por hectárea).",
        ],
    },
    "naranja": {
        "nombre_cultivo": "Naranja",
        "categoria_cultivo": "arboreo_frutal",
        "distancia_entre_surcos_m": 6.0,
        "distancia_entre_plantas_m": 5.0,
        "costo_semilla_o_plantula_unidad_cop": 6000,
        "costo_preparacion_terreno_por_ha_cop": 2500000,
        "costo_fertilizantes_por_ha_cop": 2500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1800000,
        "jornales_necesarios_por_ha_ciclo": 80,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 25000,
        "ciclo_productivo_meses": 36,
        "rango_altitud_msnm": [0, 1600],
        "rango_temperatura_c": [18, 30],
        "epoca_siembra_recomendada": "Establecer al inicio de lluvias; tierra caliente-templada.",
        "calendario_riego": "Riego en época seca; sensible a encharcamiento.",
        "calendario_fertilizacion": "Fertilización según edad del árbol.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Árbol longevo y productivo", "Mercado fresco y de jugo"],
        "fuentes_consultadas": [
            "Referencia agronómica general para cítricos (naranja) de clima cálido-templado en Colombia.",
        ],
    },

    # -----------------------------------------------------------------------
    # GRUPO F — CLIMA FRÍO ALTO / especiales (2000-3200 msnm). Referencia gral.
    # -----------------------------------------------------------------------
    "uchuva": {
        "nombre_cultivo": "Uchuva",
        "categoria_cultivo": "semipermanente",
        "distancia_entre_surcos_m": 2.5,
        "distancia_entre_plantas_m": 2.0,
        "costo_semilla_o_plantula_unidad_cop": 300,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2000000,
        "jornales_necesarios_por_ha_ciclo": 250,
        "valor_jornal_cop": 45000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 18000,
        "ciclo_productivo_meses": 12,
        "rango_altitud_msnm": [1800, 2800],
        "rango_temperatura_c": [12, 20],
        "epoca_siembra_recomendada": "Trasplante con tutorado; clima frío moderado.",
        "calendario_riego": "Humedad constante; buen drenaje.",
        "calendario_fertilizacion": "Fertilización fraccionada durante producción.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Fruta de exportación premium (physalis)", "Nicho de alto valor"],
        "fuentes_consultadas": [
            "Referencia agronómica general para uchuva (Physalis) de clima frío andino.",
        ],
    },
    "quinua": {
        "nombre_cultivo": "Quinua",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.5,
        "distancia_entre_plantas_m": 0.15,
        "costo_semilla_o_plantula_unidad_cop": 20,
        "costo_preparacion_terreno_por_ha_cop": 1200000,
        "costo_fertilizantes_por_ha_cop": 1500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 800000,
        "jornales_necesarios_por_ha_ciclo": 70,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 2500,
        "ciclo_productivo_meses": 6,
        "rango_altitud_msnm": [2400, 3200],
        "rango_temperatura_c": [6, 16],
        "epoca_siembra_recomendada": "Siembra directa; grano andino rústico de clima frío alto.",
        "calendario_riego": "Tolerante a sequía; de secano en el altiplano.",
        "calendario_fertilizacion": "Demanda moderada de nutrientes.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Grano andino de alto valor y demanda creciente", "Rústico, tolera heladas leves"],
        "fuentes_consultadas": [
            "Referencia agronómica general para quinua de clima frío alto andino.",
        ],
    },

    # -----------------------------------------------------------------------
    # GRUPO G — SISTEMAS INTENSIVOS / NOVEDOSOS (poca área, inversión fuerte).
    # Los costos y rendimientos se expresan en EQUIVALENTE POR HECTÁREA de área
    # ocupada aunque el sistema sea pequeño (el backend escala al área real).
    # Referencia técnica general (SENA/universidades); refinar con ficha propia.
    # -----------------------------------------------------------------------
    "forraje verde hidroponico de cebada": {
        "nombre_cultivo": "Forraje verde hidropónico de cebada",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.1,
        "distancia_entre_plantas_m": 0.02,
        "costo_semilla_o_plantula_unidad_cop": 5,
        "costo_preparacion_terreno_por_ha_cop": 8000000,
        "costo_fertilizantes_por_ha_cop": 3000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 500000,
        "jornales_necesarios_por_ha_ciclo": 200,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 120000,
        "ciclo_productivo_meses": 0.5,
        "rango_altitud_msnm": [0, 3200],
        "rango_temperatura_c": [8, 30],
        "epoca_siembra_recomendada": "Sistema en bandejas bajo cubierta; ciclos continuos de 12-15 días, todo el año.",
        "calendario_riego": "Riego/nebulización varias veces al día (sin sustrato o con sustrato mínimo).",
        "calendario_fertilizacion": "Solución nutritiva ligera; la semilla aporta gran parte de la energía.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Produce forraje en muy poca área todo el año", "Ideal para complementar alimentación de ganado/especies menores con poca tierra"],
        "fuentes_consultadas": [
            "Referencia técnica general (FVH, SENA/FAO): ciclos de 12-15 días, ~6-8 kg de forraje por kg de semilla. Requiere inversión inicial en estructura (estantería/bandejas/riego), por eso encaja en el perfil 'poca área, buen presupuesto'. Cifras por hectárea-equivalente aproximadas; refinar con diseño del módulo real.",
        ],
    },
    "lechuga hidroponica": {
        "nombre_cultivo": "Lechuga hidropónica",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.25,
        "distancia_entre_plantas_m": 0.25,
        "costo_semilla_o_plantula_unidad_cop": 120,
        "costo_preparacion_terreno_por_ha_cop": 20000000,
        "costo_fertilizantes_por_ha_cop": 8000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 2000000,
        "jornales_necesarios_por_ha_ciclo": 300,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": 0.3,
        "rendimiento_estimado_kg_por_ha": None,
        "ciclo_productivo_meses": 1.5,
        "rango_altitud_msnm": [0, 3000],
        "rango_temperatura_c": [10, 24],
        "epoca_siembra_recomendada": "Sistema NFT/raíz flotante bajo invernadero; producción continua todo el año.",
        "calendario_riego": "Recirculación permanente de solución nutritiva.",
        "calendario_fertilizacion": "Solución nutritiva balanceada y monitoreada (pH/EC).",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Ciclos muy cortos y continuos en poca área", "Producto limpio de alto valor para mercado gourmet/urbano"],
        "fuentes_consultadas": [
            "Referencia técnica general de hidroponía de hortalizas de hoja (SENA/universidades). Alta inversión inicial (invernadero + sistema), encaja en el perfil 'poca área, buen presupuesto'. Cifras por hectárea-equivalente aproximadas.",
        ],
    },
    "hongos orellanas": {
        "nombre_cultivo": "Hongos orellanas",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.3,
        "distancia_entre_plantas_m": 0.3,
        "costo_semilla_o_plantula_unidad_cop": 300,
        "costo_preparacion_terreno_por_ha_cop": 15000000,
        "costo_fertilizantes_por_ha_cop": 5000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1000000,
        "jornales_necesarios_por_ha_ciclo": 250,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 60000,
        "ciclo_productivo_meses": 2,
        "rango_altitud_msnm": [0, 3200],
        "rango_temperatura_c": [12, 28],
        "epoca_siembra_recomendada": "Cultivo bajo techo sobre sustrato (paja/tusa) inoculado; independiente del clima exterior.",
        "calendario_riego": "Mantener humedad alta del ambiente y del sustrato.",
        "calendario_fertilizacion": "No aplica fertilización de suelo; el sustrato es el alimento.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["No necesita tierra ni sol; aprovecha residuos agrícolas", "Producto gourmet de alto valor en poca área"],
        "fuentes_consultadas": [
            "Referencia técnica general de cultivo de orellanas (Pleurotus) sobre sustrato lignocelulósico (SENA/universidades). Requiere área acondicionada e inóculo; encaja en el perfil intensivo. Cifras por hectárea-equivalente aproximadas.",
        ],
    },
    "albahaca": {
        "nombre_cultivo": "Albahaca",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.4,
        "distancia_entre_plantas_m": 0.25,
        "costo_semilla_o_plantula_unidad_cop": 60,
        "costo_preparacion_terreno_por_ha_cop": 1500000,
        "costo_fertilizantes_por_ha_cop": 2500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1000000,
        "jornales_necesarios_por_ha_ciclo": 120,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 15000,
        "ciclo_productivo_meses": 3,
        "rango_altitud_msnm": [0, 2600],
        "rango_temperatura_c": [14, 28],
        "epoca_siembra_recomendada": "Trasplante; aromática de cortes múltiples, se adapta a varios climas.",
        "calendario_riego": "Riego frecuente y ligero.",
        "calendario_fertilizacion": "Nitrógeno para desarrollo foliar; cortes escalonados.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Aromática de alto valor con cortes repetidos", "Demanda gastronómica y de exportación en fresco/seco"],
        "fuentes_consultadas": [
            "Referencia agronómica general para albahaca (aromática culinaria) en Colombia.",
        ],
    },
    "cilantro": {
        "nombre_cultivo": "Cilantro",
        "categoria_cultivo": "ciclo_corto",
        "distancia_entre_surcos_m": 0.2,
        "distancia_entre_plantas_m": 0.05,
        "costo_semilla_o_plantula_unidad_cop": 5,
        "costo_preparacion_terreno_por_ha_cop": 1200000,
        "costo_fertilizantes_por_ha_cop": 1500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 800000,
        "jornales_necesarios_por_ha_ciclo": 90,
        "valor_jornal_cop": 50000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 12000,
        "ciclo_productivo_meses": 2,
        "rango_altitud_msnm": [0, 2800],
        "rango_temperatura_c": [12, 28],
        "epoca_siembra_recomendada": "Siembra directa densa; ciclo muy corto, siembras escalonadas.",
        "calendario_riego": "Riego frecuente y ligero.",
        "calendario_fertilizacion": "Nitrógeno para follaje; ciclo rápido.",
        "plagas_comunes": [],
        "beneficios_cultivo": ["Ciclo muy corto (rotación rápida)", "Demanda diaria constante en el mercado"],
        "fuentes_consultadas": [
            "Referencia agronómica general para cilantro en Colombia (hortaliza de hoja de ciclo corto).",
        ],
    },
}


# Sinónimos → clave canónica en TABLA_CULTIVOS (para casar lo que escriba el
# usuario o proponga la IA con la entrada correcta).
SINONIMOS = {
    "maiz amarillo": "maiz",
    "maiz blanco": "maiz",
    "frijol arbustivo": "frijol",
    "frijol voluble": "frijol",
    "platano harton": "platano",
    "banano": "platano",
    "cebolla de rama": "cebolla larga",
    "cebolla junca": "cebolla larga",
    "cebolla bulbo": "cebolla cabezona",
    "cebolla de bulbo": "cebolla cabezona",
    "papa comun": "papa",
    "papa pastusa": "papa",
    "papa sabanera": "papa",
    "brocoli": "brocoli",
    "broccoli": "brocoli",
    "col": "repollo",
    "aguacate hass": "aguacate",
    "aguacate lorena": "aguacate",
    "aguacate papelillo": "aguacate",
    "pina perolera": "pina",
    "pina gold": "pina",
    "pina oro miel": "pina",
    "naranja valencia": "naranja",
    "citricos": "naranja",
    "mandarina": "naranja",
    "tomate de arbol": "tomate de arbol",
    "tomate arbol": "tomate de arbol",
    "curuba": "granadilla",
    "fvh": "forraje verde hidroponico de cebada",
    "forraje verde hidroponico": "forraje verde hidroponico de cebada",
    "forraje hidroponico": "forraje verde hidroponico de cebada",
    "orellanas": "hongos orellanas",
    "orellana": "hongos orellanas",
    "hongos": "hongos orellanas",
    "setas": "hongos orellanas",
    "hidroponia lechuga": "lechuga hidroponica",
    "yame": "name",
    "aji dulce": "aji",
    "aji picante": "aji",
    "pimenton": "aji",
}


def buscar_en_tabla(nombre_cultivo):
    """
    Devuelve una COPIA del dict de parámetros si el cultivo está en la tabla
    curada, o None si no está (para que el llamador recurra a la IA/cache).

    El match es tolerante: normaliza tildes/mayúsculas, prueba sinónimos y
    también coincidencia por contención de palabra (ej. "papa sabanera" ->
    "papa", "tomate chonto" -> "tomate").
    """
    clave = _normalizar(nombre_cultivo)
    if not clave:
        return None

    if clave in TABLA_CULTIVOS:
        return dict(TABLA_CULTIVOS[clave])

    if clave in SINONIMOS:
        return dict(TABLA_CULTIVOS[SINONIMOS[clave]])

    # Match por palabra: si alguna clave de la tabla aparece como palabra
    # dentro del nombre pedido (o viceversa). Se prueba primero la clave más
    # larga para que "papa criolla" gane sobre "papa".
    palabras_pedido = set(clave.split())
    mejores = sorted(TABLA_CULTIVOS.keys(), key=len, reverse=True)
    for tabla_clave in mejores:
        tabla_palabras = set(tabla_clave.split())
        if tabla_palabras and tabla_palabras.issubset(palabras_pedido):
            return dict(TABLA_CULTIVOS[tabla_clave])
        if len(tabla_clave.split()) == 1 and tabla_clave in palabras_pedido:
            return dict(TABLA_CULTIVOS[tabla_clave])

    return None


def es_apto_por_temperatura(parametros, temperatura_c, margen=4):
    """
    Aptitud por rango de temperatura media, como respaldo cuando no hay dato
    de altitud (ej. la petición no trajo lat/lon). Mismo contrato que
    es_apto_por_altitud: (apto: bool|None, motivo: str).
    """
    if temperatura_c is None:
        return None, "Sin dato de temperatura para verificar aptitud."
    rango = parametros.get("rango_temperatura_c")
    if not (isinstance(rango, (list, tuple)) and len(rango) == 2):
        return None, "El cultivo no declara rango de temperatura."
    minimo, maximo = rango
    if temperatura_c < minimo - margen:
        return False, (
            f"La zona ronda ~{temperatura_c:.0f}°C, por debajo del rango apto "
            f"del cultivo ({minimo}-{maximo}°C): demasiado frío."
        )
    if temperatura_c > maximo + margen:
        return False, (
            f"La zona ronda ~{temperatura_c:.0f}°C, por encima del rango apto "
            f"del cultivo ({minimo}-{maximo}°C): demasiado cálido."
        )
    return True, (
        f"La temperatura de la zona (~{temperatura_c:.0f}°C) está dentro del "
        f"rango apto del cultivo ({minimo}-{maximo}°C)."
    )


def candidatos_por_altitud(altitud_msnm, temperatura_c=None, margen=200):
    """
    Lista de (nombre_cultivo, parametros) de la tabla curada aptos para la
    zona. Usa la ALTITUD si está disponible (señal más confiable en Colombia);
    si no, cae a la TEMPERATURA media medida; si no hay ninguna de las dos,
    retorna None (el llamador NO debe usar la tabla a ciegas: mejor pedirle
    candidatos climáticamente apropiados a la IA, como antes).
    """
    if altitud_msnm is None and temperatura_c is None:
        return None

    resultado = []
    for _clave, params in TABLA_CULTIVOS.items():
        if altitud_msnm is not None:
            apto, _ = es_apto_por_altitud(params, altitud_msnm, margen=margen)
        else:
            apto, _ = es_apto_por_temperatura(params, temperatura_c)
        if apto is not False:  # True o None (sin rango) -> se incluye
            resultado.append((params["nombre_cultivo"], dict(params)))
    return resultado


def es_apto_por_altitud(parametros, altitud_msnm, margen=200):
    """
    Verdadero/Falso/None de aptitud climática por rango de altitud, usando la
    elevación real de la zona (Open-Meteo) contra el rango del cultivo en la
    tabla. Retorna (apto: bool|None, motivo: str). None si no hay dato de
    altitud o el cultivo no declara rango (no se puede afirmar nada).

    `margen`: holgura en metros para no rechazar por estar apenas fuera del
    rango (los límites agronómicos no son cortes duros).
    """
    if altitud_msnm is None:
        return None, "Sin dato de altitud para verificar aptitud."
    rango = parametros.get("rango_altitud_msnm")
    if not (isinstance(rango, (list, tuple)) and len(rango) == 2):
        return None, "El cultivo no declara rango de altitud."

    minimo, maximo = rango
    if altitud_msnm < minimo - margen:
        return False, (
            f"La zona está a ~{altitud_msnm:.0f} msnm, por debajo del rango apto "
            f"de este cultivo ({minimo}-{maximo} msnm). Suele ser demasiado "
            f"cálido/bajo para él."
        )
    if altitud_msnm > maximo + margen:
        return False, (
            f"La zona está a ~{altitud_msnm:.0f} msnm, por encima del rango apto "
            f"de este cultivo ({minimo}-{maximo} msnm). Suele ser demasiado "
            f"frío/alto para él."
        )
    return True, (
        f"La altitud de la zona (~{altitud_msnm:.0f} msnm) está dentro del rango "
        f"apto del cultivo ({minimo}-{maximo} msnm)."
    )
