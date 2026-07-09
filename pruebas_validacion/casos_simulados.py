# pruebas_validacion/casos_simulados.py
"""
Re-ejecuta los 3 casos de prueba simulados del documento contra el backend
vigente y guarda las respuestas JSON completas + un resumen redactado por caso
+ una tabla comparativa de variables ambientales.

Salidas en resultados/:
    caso1_*.json, caso2_*.json, caso3A_*.json, caso3B_*.json
    caso1_resumen.md, caso2_resumen.md, caso3_resumen.md
    comparativa_ambiental.md
"""

from common import (
    ZONAS, timed_get, timed_post, warmup, guardar_json, guardar_texto, ahora_iso,
)


def _analisis(zona):
    z = ZONAS[zona]
    return timed_get("/analisis-terreno", {
        "lat": z["lat"], "lon": z["lon"],
        "departamento": z["departamento"], "municipio": z["municipio"],
    })


def _opciones(zona, presupuesto, area, datos_analisis):
    z = ZONAS[zona]
    return timed_post("/opciones-cultivo", {
        "departamento": z["departamento"], "municipio": z["municipio"],
        "lat": z["lat"], "lon": z["lon"],
        "presupuesto": presupuesto, "area": area, "unidad": "Metros cuadrados",
        "tipo_terreno": "plano", "datos_analisis": datos_analisis,
    }, timeout=300)


def _plan(zona, cultivo, presupuesto, area, datos_analisis):
    z = ZONAS[zona]
    return timed_post("/plan-cultivo", {
        "cultivo": cultivo, "departamento": z["departamento"], "municipio": z["municipio"],
        "lat": z["lat"], "lon": z["lon"],
        "presupuesto": presupuesto, "area": area, "unidad": "Metros cuadrados",
        "tipo_terreno": "plano", "datos_analisis": datos_analisis,
    }, timeout=300)


def _resumen_opciones_md(titulo, entrada, data):
    lineas = [f"## {titulo}", "", f"**Datos de entrada:** {entrada}", ""]
    if not isinstance(data, dict):
        lineas.append("_(respuesta no válida)_")
        return "\n".join(lineas)
    if data.get("sin_opciones_viables"):
        lineas.append(f"**Sin opciones viables.** {data.get('mensaje','')}")
        sug = data.get("sugerencia_minimo") or {}
        if sug:
            lineas.append(
                f"- Cultivo más cercano: {sug.get('cultivo_mas_cercano')} "
                f"(mínimo ~{sug.get('area_minima_rentable_m2')} m², "
                f"${sug.get('presupuesto_minimo_cop')} COP)."
            )
        return "\n".join(lineas)

    dbg = data.get("_debug_calculo", {})
    lineas.append(f"**Origen de candidatos:** {dbg.get('origen_candidatos')} · "
                  f"**Perfil:** {dbg.get('bracket_intensidad')} · "
                  f"**Altitud:** {dbg.get('altitud_msnm')} msnm")
    lineas.append("")
    lineas.append("| # | Cultivo | Rentabilidad | Ganancia (COP) | Área recom. (m²) |")
    lineas.append("|--:|---|---|--:|--:|")
    for i, c in enumerate(dbg.get("candidatos", []), 1):
        lineas.append(
            f"| {i} | {c.get('cultivo')} | {c.get('nivel_rentabilidad')} | "
            f"{c.get('ganancia_estimada_cop'):,} | {round(c.get('area_recomendada_m2') or 0):,} |"
        )
    return "\n".join(lineas)


def _escala_suelo(valor):
    """
    ISRIC SoilGrids devuelve pH en pH×10 y arcilla/arena en g/kg. Para
    presentarlos en unidades reales se dividen entre 10 (pH real, y g/kg→%).
    Un 0.0 o None de ISRIC significa 'sin dato' en ese punto (no un suelo con
    pH 0), así que se reporta como None. Esto es solo PRESENTACIÓN en el
    reporte de pruebas; no altera la lógica del backend.
    """
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return round(v / 10.0, 2)


def _extraer_ambiental(data_analisis):
    """Extrae variables ambientales del /analisis-terreno para la comparativa."""
    if not isinstance(data_analisis, dict):
        return {}
    clima = ((data_analisis.get("clima") or {}).get("data") or {})
    suelo = ((data_analisis.get("suelo") or {}).get("data") or {})
    cur = clima.get("current") or {}
    daily = clima.get("daily") or {}
    return {
        "temperatura_C": cur.get("temperature"),
        "humedad_%": cur.get("humidity"),
        "precipitacion_mm": daily.get("precipitation_sum"),
        "evapotranspiracion_mm": daily.get("evapotranspiration") or daily.get("et0_fao_evapotranspiration"),
        "pH": _escala_suelo(suelo.get("ph")),
        "arcilla_%": _escala_suelo(suelo.get("clay")),
        "arena_%": _escala_suelo(suelo.get("sand")),
    }


def main():
    warmup()
    ambiental = {}

    # ---------- CASO 1: Turmequé, $2.000.000, 1 ha ----------
    print("\n=== CASO 1: Turmequé (Boyacá) · $2.000.000 · 1 ha ===")
    _, _, a1, _ = _analisis("Turmequé")
    guardar_json("caso1_analisis.json", a1)
    ambiental["Turmequé"] = _extraer_ambiental(a1)
    _, _, o1, _ = _opciones("Turmequé", 2000000, 10000, a1)
    guardar_json("caso1_opciones.json", o1)

    # Plan del primer cultivo recomendado (si hay).
    primer = None
    if isinstance(o1, dict) and o1.get("opciones"):
        primer = o1["opciones"][0]
        _, _, p1, _ = _plan("Turmequé", primer, 2000000, 10000, a1)
        guardar_json("caso1_plan.json", p1)

    md1 = _resumen_opciones_md(
        "Caso 1 — Turmequé, Boyacá ($2.000.000 · 1 ha · plano)",
        "presupuesto $2.000.000 COP, área 1 ha (10.000 m²), terreno plano", o1,
    )
    md1 += f"\n\n**Plan detallado ejecutado para:** {primer or '(ninguno)'}\n"
    guardar_texto("caso1_resumen.md", md1)

    # ---------- CASO 2: Villavicencio, $50.000.000, 10 ha ----------
    print("\n=== CASO 2: Villavicencio (Meta) · $50.000.000 · 10 ha ===")
    _, _, a2, _ = _analisis("Villavicencio")
    guardar_json("caso2_analisis.json", a2)
    ambiental["Villavicencio"] = _extraer_ambiental(a2)
    _, _, o2, _ = _opciones("Villavicencio", 50000000, 100000, a2)
    guardar_json("caso2_opciones.json", o2)
    guardar_texto("caso2_resumen.md", _resumen_opciones_md(
        "Caso 2 — Villavicencio, Meta ($50.000.000 · 10 ha · plano)",
        "presupuesto $50.000.000 COP, área 10 ha (100.000 m²), terreno plano", o2,
    ))

    # ---------- CASO 3: A=Turmequé, B=Villavicencio, ambos $10M / 2 ha ----------
    print("\n=== CASO 3: escenarios A (Turmequé) y B (Villavicencio) · $10.000.000 · 2 ha ===")
    _, _, a3a, _ = _analisis("Turmequé")
    guardar_json("caso3A_analisis.json", a3a)
    _, _, o3a, _ = _opciones("Turmequé", 10000000, 20000, a3a)
    guardar_json("caso3A_opciones.json", o3a)

    _, _, a3b, _ = _analisis("Villavicencio")
    guardar_json("caso3B_analisis.json", a3b)
    _, _, o3b, _ = _opciones("Villavicencio", 10000000, 20000, a3b)
    guardar_json("caso3B_opciones.json", o3b)

    md3 = _resumen_opciones_md(
        "Caso 3 · Escenario A — Turmequé ($10.000.000 · 2 ha)",
        "presupuesto $10.000.000 COP, área 2 ha (20.000 m²)", o3a,
    ) + "\n\n" + _resumen_opciones_md(
        "Caso 3 · Escenario B — Villavicencio ($10.000.000 · 2 ha)",
        "presupuesto $10.000.000 COP, área 2 ha (20.000 m²)", o3b,
    )
    guardar_texto("caso3_resumen.md", md3)

    # ---------- Tabla comparativa ambiental ----------
    for zona in ("Turmequé", "Villavicencio"):
        if zona not in ambiental:
            _, _, a, _ = _analisis(zona)
            ambiental[zona] = _extraer_ambiental(a)
    for zona in list(ambiental):
        z = ZONAS[zona]
        ambiental[zona]["altitud_msnm"] = None  # se completa abajo
    from common import obtener_altitud
    for zona in ambiental:
        z = ZONAS[zona]
        ambiental[zona]["altitud_msnm"] = obtener_altitud(z["lat"], z["lon"])

    variables = ["temperatura_C", "humedad_%", "precipitacion_mm",
                 "evapotranspiracion_mm", "pH", "arcilla_%", "arena_%", "altitud_msnm"]
    comp = [f"# Comparativa ambiental — {ahora_iso()}", "",
            "| Variable | Turmequé (Boyacá) | Villavicencio (Meta) |",
            "|---|--:|--:|"]
    for v in variables:
        comp.append(f"| {v} | {ambiental.get('Turmequé',{}).get(v)} | {ambiental.get('Villavicencio',{}).get(v)} |")
    guardar_texto("comparativa_ambiental.md", "\n".join(comp))
    guardar_json("comparativa_ambiental.json", ambiental)

    print("\n✅ Casos simulados listos en resultados/")


if __name__ == "__main__":
    main()
