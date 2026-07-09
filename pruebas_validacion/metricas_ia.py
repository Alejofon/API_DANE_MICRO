# pruebas_validacion/metricas_ia.py
"""
Calcula las métricas cuantitativas de la IA (Tabla 2 del documento) sobre un
lote de escenarios (escenarios.json). Definiciones EXACTAS usadas:

- PRECISIÓN: proporción de cultivos recomendados por /opciones-cultivo que son
  (i) climáticamente aptos para la altitud REAL de la zona y (ii) declarados
  viables (ganancia > 0) por el motor. La aptitud se verifica con
  es_apto_por_altitud contra el rango de la tabla curada. Como /opciones-cultivo
  ya filtra a viables, (ii) se cumple por construcción; la métrica mide sobre
  todo la corrección climática de lo que se muestra. Los cultivos propuestos por
  IA que no están en la tabla (sin rango local) se reportan aparte como "no
  verificables localmente" y no se cuentan como aptos ni como no aptos.

- EXHAUSTIVIDAD (recall@5): para cada zona, proporción de cultivos de la tabla
  curada que son aptos por altitud Y viables con el presupuesto/área del
  escenario (verificado con /calculo-directo, que no usa IA para cultivos de la
  tabla) y que efectivamente aparecen entre las opciones devueltas. Está acotado
  por el tope de 5 opciones que muestra la app (se documenta como recall@5).

- TASA DE ERROR/ALUCINACIÓN: sobre cultivos NOVEDOSOS que NO están en la tabla
  (se fuerza la resolución por IA), proporción media de los campos técnicos
  numéricos que la capa de validación (validacion_service) tuvo que completar o
  corregir con respaldo genérico (campo `campos_estimados` de /calculo-directo).

Salidas: resultados/metricas_ia.csv y resultados/metricas_ia.md
"""

import os
import csv
import json

from common import (
    ZONAS, timed_post, warmup, obtener_altitud, guardar_texto,
    DIR_RESULTADOS, ahora_iso,
)
from services.tabla_referencia_cultivos import (
    candidatos_por_altitud, es_apto_por_altitud, buscar_en_tabla,
)

# Campos técnicos numéricos que la validación puede completar/corregir.
CAMPOS_TECNICOS = [
    "distancia_entre_surcos_m", "distancia_entre_plantas_m",
    "costo_semilla_o_plantula_unidad_cop", "costo_preparacion_terreno_por_ha_cop",
    "costo_fertilizantes_por_ha_cop", "costo_agroquimicos_control_plagas_por_ha_cop",
    "jornales_necesarios_por_ha_ciclo", "valor_jornal_cop",
    "rendimiento_estimado_kg_por_ha", "ciclo_productivo_meses", "precio_venta_kg_cop",
]


def _calculo_directo(cultivo, zona, presupuesto, area):
    z = ZONAS[zona]
    return timed_post("/calculo-directo", {
        "cultivo": cultivo, "departamento": z["departamento"], "municipio": z["municipio"],
        "presupuesto": presupuesto, "area": area, "unidad": "Metros cuadrados",
    }, timeout=120)


def _opciones(zona, presupuesto, area):
    z = ZONAS[zona]
    return timed_post("/opciones-cultivo", {
        "departamento": z["departamento"], "municipio": z["municipio"],
        "lat": z["lat"], "lon": z["lon"],
        "presupuesto": presupuesto, "area": area, "unidad": "Metros cuadrados",
    }, timeout=300)


def main():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "escenarios.json"),
              encoding="utf-8") as f:
        cfg = json.load(f)
    escenarios = cfg["escenarios"]
    novedosos = cfg.get("cultivos_novedosos_para_alucinacion", [])

    warmup()

    filas = []
    total_precision_num = total_precision_den = 0
    total_recall_num = total_recall_den = 0

    for esc in escenarios:
        zona = esc["zona"]
        presupuesto, area = esc["presupuesto"], esc["area_m2"]
        z = ZONAS[zona]
        altitud = obtener_altitud(z["lat"], z["lon"])
        print(f"\n=== {zona} ({esc['piso_termico']}, ~{altitud} msnm) · ${presupuesto:,} · {area:,} m² ===")

        # Cultivos de tabla aptos por altitud para la zona.
        apt_tabla = [n for n, _ in (candidatos_por_altitud(altitud) or [])]

        # De esos aptos, cuáles son VIABLES con este presupuesto/área (sin IA).
        apt_viables = []
        for nombre in apt_tabla:
            _, _, cd, _ = _calculo_directo(nombre, zona, presupuesto, area)
            res = (cd or {}).get("resultado", {})
            if res.get("nivel_rentabilidad") not in (None, "No viable") and (res.get("ganancia_estimada_cop") or 0) > 0:
                apt_viables.append(nombre.strip().lower())

        # Recomendaciones reales del sistema.
        _, _, op, _ = _opciones(zona, presupuesto, area)
        recomendados = (op or {}).get("opciones", []) if isinstance(op, dict) else []

        # --- Precisión ---
        prec_aptos = prec_total = no_verificables = 0
        for cultivo in recomendados:
            params = buscar_en_tabla(cultivo)
            if params is None:
                no_verificables += 1
                continue
            apto, _ = es_apto_por_altitud(params, altitud)
            prec_total += 1
            if apto is not False:
                prec_aptos += 1
        precision = (prec_aptos / prec_total) if prec_total else None

        # --- Recall@5 ---
        # Los nombres que devuelve la IA son verbosos ("Lechuga baby leaf
        # hidropónica en sistema flotante"); se canonicalizan con buscar_en_tabla
        # a su nombre de tabla antes de comparar, para no subcontar por texto.
        recomendados_canon = set()
        for c in recomendados:
            p = buscar_en_tabla(c)
            if p:
                recomendados_canon.add(p["nombre_cultivo"].strip().lower())
        recall_hit = len(recomendados_canon & set(apt_viables))
        recall = (recall_hit / len(apt_viables)) if apt_viables else None

        total_precision_num += prec_aptos
        total_precision_den += prec_total
        total_recall_num += recall_hit
        total_recall_den += len(apt_viables)

        fila = {
            "zona": zona, "piso_termico": esc["piso_termico"], "altitud_msnm": altitud,
            "presupuesto": presupuesto, "area_m2": area,
            "recomendados": ", ".join(recomendados),
            "n_recomendados": len(recomendados),
            "precision": round(precision, 3) if precision is not None else None,
            "no_verificables_ia": no_verificables,
            "apt_viables_tabla": len(apt_viables),
            "recall_at5": round(recall, 3) if recall is not None else None,
        }
        filas.append(fila)
        print(f"  recomendados: {recomendados}")
        print(f"  precisión={fila['precision']} · recall@5={fila['recall_at5']} "
              f"· apt+viables tabla={len(apt_viables)} · IA no verificables={no_verificables}")

    # --- Tasa de alucinación (cultivos novedosos, fuerza IA) ---
    print(f"\n=== Tasa de error/alucinación (IA) sobre {len(novedosos)} cultivos novedosos ===")
    aluc_filas = []
    zona_aluc = "Armenia"  # clima templado, admite muchos cultivos
    for cultivo in novedosos:
        _, _, cd, _ = _calculo_directo(cultivo, zona_aluc, 20000000, 5000)
        if not isinstance(cd, dict):
            continue
        estimados = cd.get("campos_estimados", []) or []
        estimados_tecnicos = [c for c in estimados if c in CAMPOS_TECNICOS]
        tasa = len(estimados_tecnicos) / len(CAMPOS_TECNICOS)
        aluc_filas.append({
            "cultivo": cultivo, "origen": cd.get("origen_parametros"),
            "campos_estimados": len(estimados_tecnicos), "total_campos": len(CAMPOS_TECNICOS),
            "tasa_correccion": round(tasa, 3),
        })
        print(f"  {cultivo}: origen={cd.get('origen_parametros')} · "
              f"corregidos {len(estimados_tecnicos)}/{len(CAMPOS_TECNICOS)} ({tasa:.0%})")

    precision_global = (total_precision_num / total_precision_den) if total_precision_den else None
    recall_global = (total_recall_num / total_recall_den) if total_recall_den else None
    tasa_aluc_global = (sum(a["tasa_correccion"] for a in aluc_filas) / len(aluc_filas)) if aluc_filas else None

    # --- CSV ---
    ruta_csv = os.path.join(DIR_RESULTADOS, "metricas_ia.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    # --- Markdown ---
    md = [
        f"# Métricas cuantitativas de la IA — MiSiembra ({ahora_iso()})", "",
        "## Resultados globales", "",
        f"- **Precisión global:** {precision_global:.1%}" if precision_global is not None else "- Precisión: n/d",
        f"- **Exhaustividad global (recall@5):** {recall_global:.1%}" if recall_global is not None else "- Recall: n/d",
        f"- **Tasa de corrección/alucinación IA:** {tasa_aluc_global:.1%}" if tasa_aluc_global is not None else "- Alucinación: n/d",
        "",
        "## Detalle por escenario (precisión y recall)", "",
        "| Zona | Piso | Altitud | $ | Área m² | Recomendados | Precisión | Recall@5 | Apt+viables tabla | IA no verif. |",
        "|---|---|--:|--:|--:|---|--:|--:|--:|--:|",
    ]
    for f_ in filas:
        md.append(
            f"| {f_['zona']} | {f_['piso_termico']} | {f_['altitud_msnm']} | "
            f"{f_['presupuesto']:,} | {f_['area_m2']:,} | {f_['recomendados']} | "
            f"{f_['precision']} | {f_['recall_at5']} | {f_['apt_viables_tabla']} | {f_['no_verificables_ia']} |"
        )
    md += ["", "## Tasa de error/alucinación (cultivos novedosos → fuerza IA)", "",
           "| Cultivo | Origen | Campos corregidos | Total | Tasa |",
           "|---|---|--:|--:|--:|"]
    for a in aluc_filas:
        md.append(f"| {a['cultivo']} | {a['origen']} | {a['campos_estimados']} | "
                  f"{a['total_campos']} | {a['tasa_correccion']:.0%} |")
    md += [
        "", "## Definiciones (nota metodológica)", "",
        "- **Precisión** = cultivos recomendados climáticamente aptos (altitud real vs "
        "rango de la tabla curada, `es_apto_por_altitud`) y viables (el motor solo "
        "devuelve viables) / total recomendados verificables. Cultivos propuestos por "
        "IA fuera de la tabla se cuentan aparte (columna «IA no verif.»).",
        "- **Recall@5** = cultivos de la tabla aptos por altitud Y viables con el "
        "presupuesto/área (verificado con `/calculo-directo`) que aparecen entre las 5 "
        "opciones devueltas / total de esos cultivos. Acotado por el tope de 5 opciones.",
        "- **Tasa de alucinación** = campos técnicos numéricos que la validación "
        "completó/corrigió con respaldo (`campos_estimados`) / total de campos técnicos, "
        "promediado sobre cultivos novedosos que fuerzan la resolución por IA.",
    ]
    guardar_texto("metricas_ia.md", "\n".join(md))
    print(f"\n✅ Métricas IA: precisión={precision_global}, recall={recall_global}, "
          f"alucinación={tasa_aluc_global}")


if __name__ == "__main__":
    main()
