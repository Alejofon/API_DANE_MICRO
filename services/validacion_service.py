# services/validacion_service.py
"""
Valida los parámetros crudos devueltos por agro_technical_service.py.
No decide si un cultivo es viable (eso lo hace calculo_agricola.py con
presupuesto/área reales) — aquí solo se descartan cifras técnicamente
absurdas antes de que contaminen los cálculos.

Ejemplo del caso que reportó el usuario: precio_plantula=50.000 COP con
40.000 plantas/ha implicaría 2.000 millones COP/ha solo en material
vegetal. Ese tipo de combinación se detecta aquí.
"""

# Rangos razonables en Colombia (COP, metros, meses). Son límites de
# sanidad, no valores exactos por cultivo -sirven para atrapar errores
# de orden de magnitud (ceros de más, unidades confundidas, etc).
RANGOS = {
    "distancia_entre_surcos_m": (0.05, 12.0),
    "distancia_entre_plantas_m": (0.02, 12.0),
    "costo_semilla_o_plantula_unidad_cop": (5, 60000),
    "costo_preparacion_terreno_por_ha_cop": (150000, 15000000),
    "costo_fertilizantes_por_ha_cop": (30000, 15000000),
    "costo_agroquimicos_control_plagas_por_ha_cop": (0, 12000000),
    "jornales_necesarios_por_ha_ciclo": (1, 250),
    "valor_jornal_cop": (30000, 200000),
    "ciclo_productivo_meses": (0.3, 96),
    "precio_venta_kg_cop": (20, 100000),
}

# Techo de sanidad para el costo de material vegetal por hectárea
# (plantas_por_ha * costo_unitario). Si el número de plantas por hectárea
# que implican las distancias de siembra, multiplicado por el precio
# unitario, supera esto, algo está mal (unidad confundida, cero de más, etc).
TECHO_MATERIAL_VEGETAL_POR_HA_COP = 100_000_000

CATEGORIAS_VALIDAS = {"ciclo_corto", "semipermanente", "arboreo_frutal", "extensivo"}


def validar_parametros(parametros):
    """
    Retorna (es_valido: bool, errores: list[str]).
    `parametros` es el dict crudo devuelto por agro_technical_service.
    """
    errores = []

    if "error" in parametros:
        return False, [parametros["error"]]

    categoria = parametros.get("categoria_cultivo")
    if categoria not in CATEGORIAS_VALIDAS:
        errores.append(
            f"categoria_cultivo inválida: '{categoria}' (debe ser una de {sorted(CATEGORIAS_VALIDAS)})"
        )

    for campo, (minimo, maximo) in RANGOS.items():
        valor = parametros.get(campo)
        if valor is None:
            # Algunos campos numéricos pueden ser null legítimamente
            # (ej: rendimiento_estimado_kg_por_planta si el cultivo se
            # mide por hectárea y no por planta). Solo los de costo/tiempo
            # son obligatorios.
            if campo in (
                "distancia_entre_surcos_m",
                "distancia_entre_plantas_m",
                "costo_semilla_o_plantula_unidad_cop",
                "costo_preparacion_terreno_por_ha_cop",
                "costo_fertilizantes_por_ha_cop",
                "jornales_necesarios_por_ha_ciclo",
                "valor_jornal_cop",
                "ciclo_productivo_meses",
            ):
                errores.append(f"{campo} es obligatorio y vino null")
            continue

        try:
            valor_num = float(valor)
        except (TypeError, ValueError):
            errores.append(f"{campo} no es numérico: {valor!r}")
            continue

        if not (minimo <= valor_num <= maximo):
            errores.append(
                f"{campo}={valor_num} fuera de rango razonable [{minimo}, {maximo}]"
            )

    # Chequeo cruzado: costo de material vegetal por hectárea
    surcos = parametros.get("distancia_entre_surcos_m")
    plantas_dist = parametros.get("distancia_entre_plantas_m")
    costo_unitario = parametros.get("costo_semilla_o_plantula_unidad_cop")

    if surcos and plantas_dist and costo_unitario:
        try:
            plantas_por_ha = 10000.0 / (float(surcos) * float(plantas_dist))
            costo_material_por_ha = plantas_por_ha * float(costo_unitario)
            if costo_material_por_ha > TECHO_MATERIAL_VEGETAL_POR_HA_COP:
                errores.append(
                    "Costo de material vegetal implícito por hectárea "
                    f"(≈${costo_material_por_ha:,.0f} COP) es absurdamente alto "
                    f"dadas {plantas_por_ha:,.0f} plantas/ha a ${float(costo_unitario):,.0f} c/u"
                )
        except (ZeroDivisionError, ValueError):
            errores.append("distancia_entre_surcos_m o distancia_entre_plantas_m es 0 o inválida")

    return (len(errores) == 0), errores


def resumen_errores_para_prompt(errores):
    """Convierte la lista de errores en texto legible para pedirle a la IA que corrija."""
    return "\n".join(f"- {e}" for e in errores)


# -----------------------------------------------------------------
# COMPLETAR (no solo validar): el objetivo es que la app SIEMPRE entregue
# un resultado. En vez de descartar un candidato entero porque a la IA le
# faltó un dato (frecuente en zonas menos documentadas, ej. Caquetá), se
# reemplaza SOLO el campo problemático por el valor genérico de respaldo de
# su categoría, y se deja constancia en 'campos_estimados' para ser
# transparentes con el usuario. calculo_agricola.py siempre recibe un set
# de parámetros completo y usable.
# -----------------------------------------------------------------

# Import local (no circular: calculo_agricola no importa de aquí).
from .calculo_agricola import construir_fallback

CAMPOS_PARA_CALCULO = [
    "distancia_entre_surcos_m",
    "distancia_entre_plantas_m",
    "costo_semilla_o_plantula_unidad_cop",
    "costo_preparacion_terreno_por_ha_cop",
    "costo_fertilizantes_por_ha_cop",
    "jornales_necesarios_por_ha_ciclo",
    "valor_jornal_cop",
    "ciclo_productivo_meses",
    "precio_venta_kg_cop",
]


def _numero_valido(valor, minimo=None, maximo=None):
    if valor is None:
        return False
    try:
        valor_num = float(valor)
    except (TypeError, ValueError):
        return False
    if minimo is not None and not (minimo <= valor_num <= maximo):
        return False
    return True


def completar_parametros(parametros_crudos):
    """
    Retorna (parametros_completos: dict, campos_estimados: list[str]).
    Nunca falla: si `parametros_crudos` viene vacío o con error, devuelve
    el respaldo genérico completo (categoría 'ciclo_corto' por defecto).
    """
    if not isinstance(parametros_crudos, dict) or "error" in parametros_crudos:
        return construir_fallback("ciclo_corto"), ["todos los campos (sin datos de búsqueda)"]

    categoria = parametros_crudos.get("categoria_cultivo")
    if categoria not in CATEGORIAS_VALIDAS:
        categoria = "ciclo_corto"

    respaldo = construir_fallback(categoria)
    completos = dict(parametros_crudos)
    completos["categoria_cultivo"] = categoria
    campos_estimados = []

    for campo in CAMPOS_PARA_CALCULO:
        minimo, maximo = RANGOS.get(campo, (None, None))
        if not _numero_valido(completos.get(campo), minimo, maximo):
            completos[campo] = respaldo[campo]
            campos_estimados.append(campo)

    # Rendimiento: basta con que UNO de los dos (por planta o por ha) sea
    # válido. Si ninguno lo es, se rellenan ambos desde el respaldo.
    rp_valido = _numero_valido(completos.get("rendimiento_estimado_kg_por_planta"), 0.0001, 10_000_000)
    rh_valido = _numero_valido(completos.get("rendimiento_estimado_kg_por_ha"), 0.0001, 500_000_000)
    if not rp_valido and not rh_valido:
        completos["rendimiento_estimado_kg_por_planta"] = respaldo["rendimiento_estimado_kg_por_planta"]
        completos["rendimiento_estimado_kg_por_ha"] = respaldo["rendimiento_estimado_kg_por_ha"]
        campos_estimados.append("rendimiento_estimado")

    # Chequeo cruzado de costo de material vegetal absurdo (mismo caso que
    # reportó el usuario originalmente): si persiste tras el relleno
    # anterior, se reemplaza el costo unitario de semilla/plántula.
    try:
        surcos = float(completos["distancia_entre_surcos_m"])
        dist_plantas = float(completos["distancia_entre_plantas_m"])
        plantas_por_ha = 10000.0 / (surcos * dist_plantas) if surcos > 0 and dist_plantas > 0 else 0.0
        costo_material_ha = plantas_por_ha * float(completos["costo_semilla_o_plantula_unidad_cop"])
        if costo_material_ha > TECHO_MATERIAL_VEGETAL_POR_HA_COP:
            completos["costo_semilla_o_plantula_unidad_cop"] = respaldo["costo_semilla_o_plantula_unidad_cop"]
            campos_estimados.append("costo_semilla_o_plantula_unidad_cop (costo absurdo ajustado)")
    except (ZeroDivisionError, ValueError, KeyError):
        pass

    for campo_texto in ("epoca_siembra_recomendada", "calendario_riego", "calendario_fertilizacion"):
        if not completos.get(campo_texto):
            completos[campo_texto] = respaldo[campo_texto]

    completos.setdefault("plagas_comunes", [])
    completos.setdefault("beneficios_cultivo", [])
    completos.setdefault("fuentes_consultadas", [])

    return completos, campos_estimados