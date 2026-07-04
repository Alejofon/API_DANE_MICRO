# services/calculo_agricola.py
"""
Aquí viven TODAS las matemáticas del plan de cultivo. La IA nunca calcula
números en este flujo: solo entrega parámetros (agro_technical_service)
o redacta texto (redaccion_service). Este módulo es el único lugar donde
se decide cuánta área es financiable, cuántas plantas caben, cuánto se
espera producir y cuál es la rentabilidad.
"""

from .utils_numeros import parsear_numero, formatear_cop

# -----------------------------------------------------------------
# Fallback conservador (NO es una base de datos de cultivos).
# Solo 4 arquetipos genéricos por magnitud de inversión, usados
# ÚNICAMENTE si la IA de búsqueda falla dos veces seguidas la validación.
# Sirven para no romper la app, marcando siempre "advertencia_datos": true
# para que el usuario sepa que son cifras de referencia, no específicas
# del cultivo consultado.
# -----------------------------------------------------------------
FALLBACK_POR_CATEGORIA = {
    "ciclo_corto": {
        "distancia_entre_surcos_m": 0.3,
        "distancia_entre_plantas_m": 0.25,
        "costo_semilla_o_plantula_unidad_cop": 150,
        "costo_preparacion_terreno_por_ha_cop": 1200000,
        "costo_fertilizantes_por_ha_cop": 1500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 800000,
        "jornales_necesarios_por_ha_ciclo": 40,
        "valor_jornal_cop": 60000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 15000,
        "ciclo_productivo_meses": 3,
        "precio_venta_kg_cop": 2000,
    },
    "semipermanente": {
        "distancia_entre_surcos_m": 1.0,
        "distancia_entre_plantas_m": 0.4,
        "costo_semilla_o_plantula_unidad_cop": 400,
        "costo_preparacion_terreno_por_ha_cop": 1800000,
        "costo_fertilizantes_por_ha_cop": 2500000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1200000,
        "jornales_necesarios_por_ha_ciclo": 70,
        "valor_jornal_cop": 60000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 20000,
        "ciclo_productivo_meses": 5,
        "precio_venta_kg_cop": 1800,
    },
    "arboreo_frutal": {
        "distancia_entre_surcos_m": 5.0,
        "distancia_entre_plantas_m": 5.0,
        "costo_semilla_o_plantula_unidad_cop": 12000,
        "costo_preparacion_terreno_por_ha_cop": 3000000,
        "costo_fertilizantes_por_ha_cop": 2000000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 1000000,
        "jornales_necesarios_por_ha_ciclo": 60,
        "valor_jornal_cop": 60000,
        "rendimiento_estimado_kg_por_planta": 40,
        "rendimiento_estimado_kg_por_ha": None,
        "ciclo_productivo_meses": 36,
        "precio_venta_kg_cop": 2500,
    },
    "extensivo": {
        "distancia_entre_surcos_m": 0.8,
        "distancia_entre_plantas_m": 0.2,
        "costo_semilla_o_plantula_unidad_cop": 50,
        "costo_preparacion_terreno_por_ha_cop": 1000000,
        "costo_fertilizantes_por_ha_cop": 1200000,
        "costo_agroquimicos_control_plagas_por_ha_cop": 600000,
        "jornales_necesarios_por_ha_ciclo": 25,
        "valor_jornal_cop": 60000,
        "rendimiento_estimado_kg_por_planta": None,
        "rendimiento_estimado_kg_por_ha": 6000,
        "ciclo_productivo_meses": 6,
        "precio_venta_kg_cop": 1500,
    },
}


def construir_fallback(categoria):
    base = dict(FALLBACK_POR_CATEGORIA.get(categoria, FALLBACK_POR_CATEGORIA["ciclo_corto"]))
    base["categoria_cultivo"] = categoria if categoria in FALLBACK_POR_CATEGORIA else "ciclo_corto"
    base["epoca_siembra_recomendada"] = "No disponible (dato genérico de respaldo)"
    base["calendario_riego"] = "No disponible (dato genérico de respaldo)"
    base["calendario_fertilizacion"] = "No disponible (dato genérico de respaldo)"
    base["plagas_comunes"] = []
    base["beneficios_cultivo"] = []
    base["fuentes_consultadas"] = []
    return base


def _clasificar_rentabilidad(ganancia, costo_invertido):
    if costo_invertido <= 0:
        return "Baja"
    margen = ganancia / costo_invertido
    # Con datos estimados (búsqueda web + respaldo genérico) un margen
    # ligeramente negativo puede ser error de estimación, no inviabilidad
    # real. Solo se marca "No viable" ante una pérdida clara (>30%).
    if margen <= -0.30:
        return "No viable"
    if margen <= 0.15:
        return "Baja"
    if margen < 0.5:
        return "Media"
    return "Alta"


# Nombres de respaldo por categoría, SOLO para el caso extremo en que la
# búsqueda web falle por completo (error de red, JSON inválido, etc) al
# proponer candidatos. No son "la base de datos de cultivos": son apenas
# 3 nombres ampliamente comunes en el agro colombiano por categoría, para
# que la app nunca se quede sin ninguna opción que mostrar. Siempre se
# marcan con advertencia de datos estimados.
NOMBRES_RESPALDO_POR_CATEGORIA = {
    "ciclo_corto": ["Tomate", "Cilantro", "Lechuga"],
    "semipermanente": ["Fríjol", "Maíz", "Ahuyama"],
    "arboreo_frutal": ["Plátano", "Cacao", "Cítricos"],
    "extensivo": ["Yuca", "Arroz", "Caña panelera"],
}


def construir_candidatos_respaldo():
    """
    Devuelve una lista de (nombre_cultivo, parametros_respaldo) para usar
    ÚNICAMENTE cuando obtener_candidatos_cultivo falló por completo (no
    cuando solo faltaron algunos campos: para eso está completar_parametros
    en validacion_service.py).
    """
    candidatos = []
    for categoria, nombres in NOMBRES_RESPALDO_POR_CATEGORIA.items():
        for nombre in nombres:
            candidatos.append((nombre, construir_fallback(categoria)))
    return candidatos


def calcular_plan(parametros, presupuesto_cop, area_disponible_m2, precio_dane_kg=None):
    """
    Recibe los parámetros crudos (ya validados) del cultivo y hace TODA
    la matemática. Devuelve un dict con los resultados calculados,
    listos para que redaccion_service.py solo escriba el texto alrededor.

    `precio_dane_kg`: si el endpoint /analisis-terreno trajo un precio de
    mercado real para el grupo del cultivo, se prioriza sobre el precio
    que devolvió la IA de búsqueda (fuente más confiable y ya en la BD).
    """
    presupuesto = parsear_numero(presupuesto_cop)
    area_disponible_ha = area_disponible_m2 / 10000.0

    surcos = float(parametros["distancia_entre_surcos_m"])
    dist_plantas = float(parametros["distancia_entre_plantas_m"])
    plantas_por_ha = 10000.0 / (surcos * dist_plantas) if surcos > 0 and dist_plantas > 0 else 0.0

    costo_material_vegetal_ha = plantas_por_ha * float(parametros["costo_semilla_o_plantula_unidad_cop"])
    costo_mano_obra_ha = (
        float(parametros["jornales_necesarios_por_ha_ciclo"]) * float(parametros["valor_jornal_cop"])
    )
    costo_preparacion_ha = float(parametros["costo_preparacion_terreno_por_ha_cop"])
    costo_fertilizantes_ha = float(parametros["costo_fertilizantes_por_ha_cop"])
    costo_agroquimicos_ha = float(parametros.get("costo_agroquimicos_control_plagas_por_ha_cop") or 0)

    costo_total_por_ha = (
        costo_material_vegetal_ha
        + costo_mano_obra_ha
        + costo_preparacion_ha
        + costo_fertilizantes_ha
        + costo_agroquimicos_ha
    )

    # --- Área financiable y recomendada -------------------------------
    if costo_total_por_ha > 0:
        area_financiable_ha = presupuesto / costo_total_por_ha
    else:
        area_financiable_ha = area_disponible_ha  # evita división por 0

    area_recomendada_ha = min(area_financiable_ha, area_disponible_ha)
    area_recomendada_ha = max(area_recomendada_ha, 0.0)
    area_recomendada_m2 = area_recomendada_ha * 10000.0

    # --- Producción e ingresos ------------------------------------------
    numero_plantas_estimadas = round(area_recomendada_ha * plantas_por_ha)

    rendimiento_por_planta = parametros.get("rendimiento_estimado_kg_por_planta")
    rendimiento_por_ha = parametros.get("rendimiento_estimado_kg_por_ha")

    if rendimiento_por_planta:
        produccion_estimada_kg = numero_plantas_estimadas * float(rendimiento_por_planta)
    elif rendimiento_por_ha:
        produccion_estimada_kg = area_recomendada_ha * float(rendimiento_por_ha)
    else:
        produccion_estimada_kg = 0.0

    precio_kg = precio_dane_kg or parametros.get("precio_venta_kg_cop") or 0
    precio_kg = float(precio_kg)

    ingreso_estimado = produccion_estimada_kg * precio_kg
    costo_real_invertido = area_recomendada_ha * costo_total_por_ha
    ganancia_estimada = ingreso_estimado - costo_real_invertido

    nivel_rentabilidad = _clasificar_rentabilidad(ganancia_estimada, costo_real_invertido)

    # --- Área mínima rentable: la escala más pequeña donde el ingreso ----
    # supera el costo, dado que muchos costos (preparación de terreno,
    # por ejemplo) no bajan proporcionalmente al reducir el área.
    # Aproximación: 20 m² o el área que cubra al menos el costo de
    # preparación del terreno, lo que sea mayor.
    if costo_total_por_ha > 0 and ingreso_estimado > 0 and area_recomendada_ha > 0:
        ingreso_por_ha = ingreso_estimado / area_recomendada_ha
        margen_por_ha = ingreso_por_ha - costo_total_por_ha
        if margen_por_ha > 0:
            area_minima_ha = max(costo_preparacion_ha / ingreso_por_ha, 0.002)  # piso ~20 m²
        else:
            area_minima_ha = None
    else:
        area_minima_ha = None

    ciclo_meses = float(parametros.get("ciclo_productivo_meses") or 0)
    retorno_inversion_meses = ciclo_meses if ganancia_estimada > 0 else None

    return {
        "plantas_por_ha": round(plantas_por_ha, 1),
        "costo_material_vegetal_ha": round(costo_material_vegetal_ha),
        "costo_mano_obra_ha": round(costo_mano_obra_ha),
        "costo_total_establecimiento_ha": round(costo_total_por_ha),
        "area_disponible_ha": round(area_disponible_ha, 4),
        "area_financiable_ha": round(area_financiable_ha, 4),
        "area_recomendada_ha": round(area_recomendada_ha, 4),
        "area_recomendada_m2": round(area_recomendada_m2, 1),
        "numero_plantas_estimadas": numero_plantas_estimadas,
        "produccion_estimada_kg": round(produccion_estimada_kg, 1),
        "precio_kg_usado_cop": round(precio_kg, 1),
        "precio_fuente": "DANE (precios_mercado del análisis de terreno)" if precio_dane_kg else "Estimado por IA de búsqueda técnica",
        "ingreso_estimado_cop": round(ingreso_estimado),
        "costo_real_invertido_cop": round(costo_real_invertido),
        "ganancia_estimada_cop": round(ganancia_estimada),
        "nivel_rentabilidad": nivel_rentabilidad,
        "retorno_inversion_meses": retorno_inversion_meses,
        "area_minima_rentable_ha": round(area_minima_ha, 4) if area_minima_ha else None,
        "presupuesto_minimo_recomendado_cop": round(costo_total_por_ha * (area_minima_ha or 0.002)) if costo_total_por_ha else None,
        "ciclo_productivo_meses": ciclo_meses,
    }


def formatear_resultados_para_ui(calculado, parametros):
    """
    Traduce los resultados numéricos crudos a los strings que la UI de
    Flutter necesita (el widget solo hace .toString() sobre estos campos,
    así que ya deben venir legibles).
    """
    area_ha = calculado["area_recomendada_ha"]
    area_texto = (
        f"{round(area_ha * 10000)} m² (≈{area_ha:.3f} ha) de las "
        f"{calculado['area_disponible_ha']:.3f} ha disponibles"
    )

    distancia_texto = (
        f"{parametros['distancia_entre_surcos_m']} m entre surcos x "
        f"{parametros['distancia_entre_plantas_m']} m entre plantas"
    )

    produccion_texto = f"≈{calculado['produccion_estimada_kg']:.0f} kg por ciclo"

    area_minima_texto = (
        f"≈{round(calculado['area_minima_rentable_ha'] * 10000)} m²"
        if calculado["area_minima_rentable_ha"]
        else "No se identificó una escala mínima rentable con los datos disponibles"
    )

    presupuesto_minimo_texto = (
        formatear_cop(calculado["presupuesto_minimo_recomendado_cop"])
        if calculado["presupuesto_minimo_recomendado_cop"]
        else "No disponible"
    )

    ganancia_texto = formatear_cop(calculado["ganancia_estimada_cop"])

    return {
        "area_realmente_cultivable": area_texto,
        "numero_plantas_estimadas": calculado["numero_plantas_estimadas"],
        "distancia_siembra": distancia_texto,
        "produccion_estimada": produccion_texto,
        "area_minima_rentable": area_minima_texto,
        "presupuesto_minimo_recomendado": presupuesto_minimo_texto,
        "ganancia_estimada_por_cosecha": ganancia_texto,
        "retorno_inversion_meses": calculado["retorno_inversion_meses"],
        "nivel_rentabilidad": calculado["nivel_rentabilidad"],
    }