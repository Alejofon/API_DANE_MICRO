# pruebas_validacion/benchmark_tiempos.py
"""
Mide los TIEMPOS DE RESPUESTA (ms) del backend de MiSiembra contra producción.

Para cada endpoint crítico ejecuta n repeticiones y reporta promedio, mínimo,
máximo y percentil 95. Distingue los caminos que pasan por IA (lentos, se miden
con pocas repeticiones para no gastar de más) de los deterministas (rápidos).

Uso:
    python pruebas_validacion/benchmark_tiempos.py [--reps N]

Salidas: resultados/tiempos.csv  y  resultados/tiempos.md
"""

import csv
import sys
import os

from common import (
    ZONAS, timed_get, timed_post, warmup, resumen_estadistico,
    guardar_texto, DIR_RESULTADOS, ahora_iso, BASE_URL,
)

REPS = 10
if "--reps" in sys.argv:
    try:
        REPS = int(sys.argv[sys.argv.index("--reps") + 1])
    except (ValueError, IndexError):
        pass


def _analisis_params(zona):
    z = ZONAS[zona]
    return {"lat": z["lat"], "lon": z["lon"], "departamento": z["departamento"], "municipio": z["municipio"]}


def _cuerpo_opciones(zona, presupuesto, area, datos_analisis=None):
    z = ZONAS[zona]
    return {
        "departamento": z["departamento"], "municipio": z["municipio"],
        "lat": z["lat"], "lon": z["lon"],
        "presupuesto": presupuesto, "area": area, "unidad": "Metros cuadrados",
        "tipo_terreno": "plano", "datos_analisis": datos_analisis,
    }


def _cuerpo_plan(zona, cultivo, presupuesto, area, datos_analisis=None):
    body = _cuerpo_opciones(zona, presupuesto, area, datos_analisis)
    body["cultivo"] = cultivo
    return body


def medir(nombre, descripcion, fn, reps, incurre_ia):
    """Ejecuta `fn` (retorna (status, elapsed_ms, data, err)) `reps` veces."""
    print(f"\n[{nombre}] {descripcion} (reps={reps}, IA={'sí' if incurre_ia else 'no'})")
    tiempos, estados = [], []
    for i in range(reps):
        status, elapsed, data, err = fn()
        estados.append(status)
        if err:
            print(f"  rep {i+1}: ERROR {err} ({elapsed/1000:.1f}s)")
        else:
            tiempos.append(elapsed)
            print(f"  rep {i+1}: HTTP {status} en {elapsed/1000:.2f}s")
    stats = resumen_estadistico(tiempos)
    stats.update({
        "endpoint": nombre, "descripcion": descripcion,
        "incurre_ia": incurre_ia, "ok": estados.count(200), "reps": reps,
    })
    return stats


def main():
    warmup()
    # Pre-cachear una zona para medir /opciones-cultivo "con caché".
    print("\n[pre] Calentando caché de opciones en Tocancipá (una consulta con IA, se descarta)...")
    timed_post("/opciones-cultivo", _cuerpo_opciones("Tocancipá", 5000000, 5000), timeout=300)

    filas = []

    # (a) /analisis-terreno — determinista
    filas.append(medir(
        "/analisis-terreno", "Clima+suelo+precios (Tocancipá)",
        lambda: timed_get("/analisis-terreno", _analisis_params("Tocancipá")),
        REPS, incurre_ia=False,
    ))

    # (b) /opciones-cultivo ZONA NUEVA (primera vez, pasa por IA) — 1 rep
    filas.append(medir(
        "/opciones-cultivo (zona nueva, IA)",
        "Municipio poco común, fuerza fallo de caché + búsqueda IA",
        lambda: timed_post("/opciones-cultivo", _cuerpo_opciones("Valledupar", 8000000, 8000), timeout=300),
        1, incurre_ia=True,
    ))

    # (c) /opciones-cultivo ZONA CACHEADA — determinista tras el pre-calentado
    filas.append(medir(
        "/opciones-cultivo (con caché)", "Misma zona ya cacheada (Tocancipá)",
        lambda: timed_post("/opciones-cultivo", _cuerpo_opciones("Tocancipá", 5000000, 5000), timeout=300),
        REPS, incurre_ia=False,
    ))

    # (d) /plan-cultivo cultivo APTO (tabla curada + redacción IA)
    filas.append(medir(
        "/plan-cultivo (apto)", "Zanahoria en Tocancipá (apto; incluye redacción IA)",
        lambda: timed_post("/plan-cultivo", _cuerpo_plan("Tocancipá", "Zanahoria", 12000000, 10000), timeout=300),
        max(3, REPS // 2), incurre_ia=True,
    ))

    # (e) /plan-cultivo cultivo NO APTO por clima (corta rápido, sin IA)
    filas.append(medir(
        "/plan-cultivo (no apto)", "Cacao en Turmequé (rechazo por altitud, sin IA)",
        lambda: timed_post("/plan-cultivo", _cuerpo_plan("Turmequé", "Cacao", 20000000, 10000), timeout=120),
        REPS, incurre_ia=False,
    ))

    # (f) /calculo-directo — determinista
    filas.append(medir(
        "/calculo-directo", "Zanahoria en Tocancipá (motor puro, sin IA)",
        lambda: timed_post("/calculo-directo", {
            "cultivo": "Zanahoria", "departamento": "CUNDINAMARCA", "municipio": "TOCANCIPA",
            "presupuesto": 12000000, "area": 10000, "unidad": "Metros cuadrados",
        }, timeout=120),
        REPS, incurre_ia=False,
    ))

    # (g) /buscar-insumos — Google Places
    z = ZONAS["Tocancipá"]
    filas.append(medir(
        "/buscar-insumos", "Proveedores cercanos (Google Places)",
        lambda: timed_get("/buscar-insumos", {"lat": z["lat"], "lon": z["lon"]}, timeout=120),
        max(3, REPS // 2), incurre_ia=False,
    ))

    # --- CSV ---
    ruta_csv = os.path.join(DIR_RESULTADOS, "tiempos.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "endpoint", "descripcion", "incurre_ia", "reps", "ok",
            "promedio_ms", "min_ms", "max_ms", "p95_ms",
        ])
        w.writeheader()
        for fila in filas:
            w.writerow({k: fila.get(k) for k in w.fieldnames})

    # --- Markdown ---
    md = [
        f"# Tiempos de respuesta del backend — MiSiembra",
        f"",
        f"- **Backend:** {BASE_URL}",
        f"- **Fecha de ejecución:** {ahora_iso()}",
        f"- **Repeticiones (deterministas):** {REPS}",
        f"",
        f"| Endpoint | IA | Reps | OK | Promedio (ms) | Mín (ms) | Máx (ms) | P95 (ms) |",
        f"|---|:--:|:--:|:--:|--:|--:|--:|--:|",
    ]
    for fila in filas:
        md.append(
            f"| {fila['endpoint']} | {'Sí' if fila['incurre_ia'] else 'No'} | "
            f"{fila['reps']} | {fila['ok']} | {fila['promedio_ms']} | "
            f"{fila['min_ms']} | {fila['max_ms']} | {fila['p95_ms']} |"
        )
    md += [
        "",
        "> Nota: los endpoints marcados con IA dependen de OpenAI (búsqueda web y/o "
        "redacción) y de la latencia variable de la red; sus tiempos no son "
        "comparables con los deterministas. La primera consulta de una zona por "
        "`/opciones-cultivo` pasa por búsqueda IA (minutos); las siguientes salen de "
        "caché en Postgres (milisegundos). El primer request tras inactividad incluye "
        "el arranque en frío de Render (plan gratuito) y se descartó del muestreo.",
    ]
    guardar_texto("tiempos.md", "\n".join(md))
    print(f"\n✅ Listo: {ruta_csv}  y  resultados/tiempos.md")


if __name__ == "__main__":
    main()
