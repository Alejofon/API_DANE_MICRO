# pruebas_validacion/casos_limite.py
"""
Evidencia del COMPORTAMIENTO HONESTO del sistema en casos límite:
  (a) cultivo no apto por clima  -> respuesta "no apto", sin gastar IA.
  (b) presupuesto ínfimo         -> sin_opciones_viables + mínimo requerido.
  (c) terreno grande, poco dinero -> área recomendada = fracción del terreno.

Salidas: resultados/casoslimite_*.json y resultados/casos_limite.md
"""

from common import ZONAS, timed_post, warmup, guardar_json, guardar_texto, ahora_iso


def main():
    warmup()
    md = [f"# Casos límite — comportamiento honesto ({ahora_iso()})", ""]

    # (a) Cacao en Turmequé (2.400 msnm) -> no apto por altitud, corta sin IA.
    z = ZONAS["Turmequé"]
    _, ms_a, ra, _ = timed_post("/plan-cultivo", {
        "cultivo": "Cacao", "departamento": z["departamento"], "municipio": z["municipio"],
        "lat": z["lat"], "lon": z["lon"],
        "presupuesto": 20000000, "area": 10000, "unidad": "Metros cuadrados",
    }, timeout=120)
    guardar_json("casoslimite_a_cacao_noapto.json", ra)
    apto = (ra or {}).get("_debug_calculo", {}).get("apto_para_la_zona")
    motivo = (ra or {}).get("_debug_calculo", {}).get("motivo_aptitud")
    md += [
        "## (a) Cultivo no apto por clima — Cacao en Turmequé (~2.400 msnm)",
        f"- `apto_para_la_zona`: **{apto}**",
        f"- Motivo: {motivo}",
        f"- Tiempo de respuesta: {ms_a/1000:.2f}s (corta sin llamar a la IA)",
        "",
    ]

    # (b) Presupuesto ínfimo -> sin_opciones_viables.
    z = ZONAS["Tocancipá"]
    _, _, rb, _ = timed_post("/opciones-cultivo", {
        "departamento": z["departamento"], "municipio": z["municipio"],
        "lat": z["lat"], "lon": z["lon"],
        "presupuesto": 50000, "area": 100, "unidad": "Metros cuadrados",
    }, timeout=300)
    guardar_json("casoslimite_b_presupuesto_infimo.json", rb)
    sug = (rb or {}).get("sugerencia_minimo") or {}
    md += [
        "## (b) Presupuesto insuficiente — $50.000 COP, 100 m² (Tocancipá)",
        f"- `sin_opciones_viables`: **{(rb or {}).get('sin_opciones_viables')}**",
        f"- Mensaje: {(rb or {}).get('mensaje')}",
        f"- Cultivo más cercano: {sug.get('cultivo_mas_cercano')} — "
        f"mínimo ~{sug.get('area_minima_rentable_m2')} m², ${sug.get('presupuesto_minimo_cop')} COP",
        "",
    ]

    # (c) Terreno grande, poco dinero -> área recomendada parcial.
    _, _, rc, _ = timed_post("/calculo-directo", {
        "cultivo": "Papa", "departamento": "CUNDINAMARCA", "municipio": "TOCANCIPA",
        "presupuesto": 1000000, "area": 5000000, "unidad": "Metros cuadrados",
    }, timeout=120)
    guardar_json("casoslimite_c_terreno_grande.json", rc)
    res = (rc or {}).get("resultado", {})
    area_rec = res.get("area_recomendada_m2")
    md += [
        "## (c) Terreno grande, poco dinero — Papa, $1.000.000 COP, 500 ha",
        f"- Área disponible: 5.000.000 m² (500 ha)",
        f"- **Área recomendada: {round(area_rec or 0):,} m²** (fracción del terreno "
        f"que el presupuesto cubre)",
        f"- Nivel: {res.get('nivel_rentabilidad')} · Ganancia: "
        f"${(res.get('ganancia_estimada_cop') or 0):,} COP",
        "",
    ]

    guardar_texto("casos_limite.md", "\n".join(md))
    print("✅ Casos límite listos en resultados/casos_limite.md")


if __name__ == "__main__":
    main()
