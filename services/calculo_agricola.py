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


# Piso realista de "área mínima rentable" por categoría, en hectáreas.
# Coincide con las reglas de área mínima que options_prompt.dart ya exige
# al proponer cultivos (50-100 m² ciclo corto, 200-500 m² semipermanente,
# 5000 m²+ arbóreo/frutal, 1 ha+ extensivo). Reemplaza el cálculo puramente
# matemático anterior, que podía dar fracciones de metro cuadrado sin
# sentido práctico (ver corrección: no se puede comprar el 0.01% de un
# bulto de fertilizante ni contratar una fracción de jornal).
PISO_AREA_MINIMA_HA_POR_CATEGORIA = {
    "ciclo_corto": 0.0075,       # ~75 m²
    "semipermanente": 0.035,     # ~350 m²
    "arboreo_frutal": 0.5,       # 5000 m²
    "extensivo": 1.0,            # 1 ha
}

# Tope de sanidad para rendimiento POR PLANTA, en kg. Una planta herbácea
# (papa, tomate, hortaliza) no puede rendir lo mismo que un árbol frutal
# maduro — un tope único para todas las categorías dejaba pasar absurdos
# como "150 kg/planta" en un cultivo de ciclo corto.
TECHO_RENDIMIENTO_POR_PLANTA_KG = {
    "ciclo_corto": 15,
    "semipermanente": 30,
    "arboreo_frutal": 300,
    "extensivo": 15,
}


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
    ciclo_meses = float(parametros.get("ciclo_productivo_meses") or 0)

    # --- Densidad de siembra -------------------------------------------
    # Defensa adicional: validacion_service.completar_parametros ya debería
    # garantizar distancias > 0, pero nunca se divide por cero aquí aunque
    # llegue algo inesperado.
    surcos = float(parametros["distancia_entre_surcos_m"]) or 0.3
    dist_plantas = float(parametros["distancia_entre_plantas_m"]) or 0.25
    if surcos <= 0:
        surcos = 0.3
    if dist_plantas <= 0:
        dist_plantas = 0.25
    plantas_por_ha = max(10000.0 / (surcos * dist_plantas), 1.0)

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

    # --- Costos fijos vs variables --------------------------------------
    # Sembrar una parcela pequeña NO cuesta simplemente "área% del costo
    # por hectárea": existen costos que no bajan proporcionalmente al
    # reducir el área (transporte, análisis de suelo, herramientas,
    # desplazamiento, jornales mínimos indivisibles). Se modela un 10%
    # del costo por hectárea como costo fijo único, y el 90% restante sí
    # escala con el área. Es una simplificación deliberada, pero evita que
    # "microparcelas" parezcan viables solo porque todo escalaba a cero.
    FRACCION_COSTO_FIJO = 0.10
    costo_fijo_cop = FRACCION_COSTO_FIJO * costo_total_por_ha
    costo_variable_por_ha = (1 - FRACCION_COSTO_FIJO) * costo_total_por_ha

    def costo_de_area(area_ha):
        if area_ha <= 0:
            return 0.0
        return costo_fijo_cop + costo_variable_por_ha * area_ha

    # --- Piso de escala mínima práctica + presupuesto mínimo REAL -------
    # Antes solo se limitaba el área a lo financiable (presupuesto/costo),
    # lo cual matemáticamente siempre "encuentra" un área positiva por
    # pequeña que sea. Ahora se compara el presupuesto contra el costo real
    # de establecer la escala mínima práctica: si no alcanza, el proyecto
    # es "No viable" de una vez, en vez de reducir el área infinitamente.
    categoria = parametros.get("categoria_cultivo")
    piso_area_ha = PISO_AREA_MINIMA_HA_POR_CATEGORIA.get(categoria, PISO_AREA_MINIMA_HA_POR_CATEGORIA["ciclo_corto"])
    presupuesto_minimo_piso_cop = costo_de_area(piso_area_ha)

    tierra_insuficiente = area_disponible_ha < piso_area_ha
    presupuesto_insuficiente = presupuesto < presupuesto_minimo_piso_cop

    ganancia_atipica = False

    if tierra_insuficiente or presupuesto_insuficiente:
        area_financiable_ha = max((presupuesto - costo_fijo_cop) / costo_variable_por_ha, 0.0) if costo_variable_por_ha > 0 else 0.0
        area_recomendada_ha = 0.0
        numero_plantas_estimadas = 0
        produccion_estimada_kg = 0.0
        precio_kg = float(precio_dane_kg or parametros.get("precio_venta_kg_cop") or 0)
        ingreso_estimado = 0.0
        costo_real_invertido = 0.0
        ganancia_estimada = 0.0
        nivel_rentabilidad = "No viable"
        retorno_inversion_meses = None

        if tierra_insuficiente and presupuesto_insuficiente:
            motivo_no_viable = (
                f"El área disponible ({area_disponible_ha * 10000:.0f} m²) y el presupuesto "
                f"(${presupuesto:,.0f} COP) son insuficientes: se necesitan al menos "
                f"~{piso_area_ha * 10000:.0f} m² y ${presupuesto_minimo_piso_cop:,.0f} COP "
                f"para establecer este cultivo a su escala mínima práctica."
            )
        elif tierra_insuficiente:
            motivo_no_viable = (
                f"El área disponible ({area_disponible_ha * 10000:.0f} m²) es menor a la "
                f"escala mínima práctica de este cultivo (~{piso_area_ha * 10000:.0f} m²)."
            )
        else:
            motivo_no_viable = (
                f"El presupuesto (${presupuesto:,.0f} COP) es menor al mínimo real para "
                f"sembrar la escala mínima práctica de este cultivo "
                f"(~{piso_area_ha * 10000:.0f} m², ${presupuesto_minimo_piso_cop:,.0f} COP)."
            )
    else:
        motivo_no_viable = None

        area_financiable_ha = (
            max((presupuesto - costo_fijo_cop) / costo_variable_por_ha, 0.0)
            if costo_variable_por_ha > 0 else area_disponible_ha
        )
        area_recomendada_ha = min(area_financiable_ha, area_disponible_ha)
        area_recomendada_ha = max(area_recomendada_ha, piso_area_ha)
        area_recomendada_ha = min(area_recomendada_ha, area_disponible_ha)  # nunca exceder lo disponible

        numero_plantas_estimadas = round(area_recomendada_ha * plantas_por_ha)
        if area_recomendada_ha > 0 and numero_plantas_estimadas <= 0:
            numero_plantas_estimadas = max(round(area_recomendada_ha * plantas_por_ha), 1)

        # --- Rendimiento: validado, no aceptado a ciegas -----------------
        # Rangos de sanidad amplios pero reales: una planta que rinda más
        # de 300 kg, o una hectárea que rinda más de 200 toneladas, casi
        # seguro es un error de unidades de la IA, no un dato real.
        rendimiento_por_planta = parametros.get("rendimiento_estimado_kg_por_planta")
        rendimiento_por_ha = parametros.get("rendimiento_estimado_kg_por_ha")

        def _rendimiento_valido(valor, maximo):
            try:
                v = float(valor)
                return 0 < v <= maximo
            except (TypeError, ValueError):
                return False

        # Tope por categoría: una planta herbácea (papa, tomate, hortaliza)
        # no puede rendir lo mismo que un árbol frutal maduro. Un tope único
        # para todos permitía absurdos como "150 kg/planta" en un cultivo
        # de ciclo corto.
        techo_por_planta = TECHO_RENDIMIENTO_POR_PLANTA_KG.get(categoria, TECHO_RENDIMIENTO_POR_PLANTA_KG["ciclo_corto"])

        if _rendimiento_valido(rendimiento_por_planta, techo_por_planta):
            produccion_estimada_kg = numero_plantas_estimadas * float(rendimiento_por_planta)
        elif _rendimiento_valido(rendimiento_por_ha, 200_000):
            produccion_estimada_kg = area_recomendada_ha * float(rendimiento_por_ha)
        else:
            produccion_estimada_kg = 0.0

        # --- Precio: validado, no aceptado a ciegas ----------------------
        # Tope de sanidad genérico (no específico por cultivo): por encima
        # de esto, casi seguro es una alucinación de la IA, no un precio
        # real de un cultivo agrícola común en Colombia.
        TECHO_PRECIO_KG_COP = 80_000
        precio_kg = precio_dane_kg or parametros.get("precio_venta_kg_cop") or 0
        try:
            precio_kg = float(precio_kg)
        except (TypeError, ValueError):
            precio_kg = 0.0
        if precio_kg > TECHO_PRECIO_KG_COP:
            precio_kg = TECHO_PRECIO_KG_COP

        ingreso_estimado = produccion_estimada_kg * precio_kg
        costo_real_invertido = costo_de_area(area_recomendada_ha)

        # --- Validación final de coherencia ------------------------------
        # No debería ocurrir dado que area_recomendada_ha ya respeta el
        # presupuesto, pero se deja como red de seguridad explícita.
        if costo_real_invertido > presupuesto:
            costo_real_invertido = presupuesto
        if area_recomendada_ha > area_disponible_ha:
            area_recomendada_ha = area_disponible_ha

        ganancia_estimada = ingreso_estimado - costo_real_invertido

        if produccion_estimada_kg <= 0:
            nivel_rentabilidad = "No viable"
            motivo_no_viable = (
                "No fue posible estimar una producción mayor a cero con los "
                "datos de rendimiento disponibles para este cultivo."
            )
        else:
            nivel_rentabilidad = _clasificar_rentabilidad(ganancia_estimada, costo_real_invertido)
            if costo_real_invertido > 0 and (ganancia_estimada / costo_real_invertido) > 10:
                ganancia_atipica = True

        # --- Retorno de inversión: por ciclos, no "una cosecha alcanza" --
        if ganancia_estimada > 0 and ciclo_meses > 0:
            ciclos_para_recuperar = costo_real_invertido / ganancia_estimada
            retorno_inversion_meses = round(ciclos_para_recuperar * ciclo_meses, 1)
        else:
            retorno_inversion_meses = None

    area_recomendada_m2 = area_recomendada_ha * 10000.0

    return {
        "plantas_por_ha": round(plantas_por_ha, 1),
        "costo_material_vegetal_ha": round(costo_material_vegetal_ha),
        "costo_mano_obra_ha": round(costo_mano_obra_ha),
        "costo_total_establecimiento_ha": round(costo_total_por_ha),
        "costo_fijo_cop": round(costo_fijo_cop),
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
        "ganancia_atipica": ganancia_atipica,
        "nivel_rentabilidad": nivel_rentabilidad,
        "motivo_no_viable": motivo_no_viable,
        "retorno_inversion_meses": retorno_inversion_meses,
        "area_minima_rentable_ha": round(piso_area_ha, 4),
        "presupuesto_minimo_recomendado_cop": round(presupuesto_minimo_piso_cop),
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

    area_minima_texto = f"≈{round(calculado['area_minima_rentable_ha'] * 10000)} m²"
    presupuesto_minimo_texto = formatear_cop(calculado["presupuesto_minimo_recomendado_cop"])

    if calculado["nivel_rentabilidad"] == "No viable" and calculado.get("motivo_no_viable"):
        ganancia_texto = calculado["motivo_no_viable"]
    else:
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