# pruebas_validacion/generar_resumen.py
"""
Consolida los .md/.json ya generados por los demás scripts en un único
RESUMEN_GENERAL.md, listo para transcribir al documento de grado.
Se ejecuta al final; no vuelve a llamar al backend.
"""

import os
import json

from common import DIR_RESULTADOS, ahora_iso, BASE_URL

RAIZ = os.path.dirname(os.path.abspath(__file__))


def _leer(nombre):
    ruta = os.path.join(DIR_RESULTADOS, nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    return f"_(no se generó {nombre})_"


def _leer_json(nombre):
    ruta = os.path.join(DIR_RESULTADOS, nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return None


def main():
    partes = [
        f"# MiSiembra — Resumen general de pruebas de software",
        f"",
        f"- **Backend probado:** {BASE_URL}",
        f"- **Generado:** {ahora_iso()}",
        f"",
        f"Este archivo consolida todos los resultados de la carpeta "
        f"`pruebas_validacion/`. Cada sección corresponde a un entregable del plan "
        f"de pruebas del documento de grado.",
        f"",
        "---", "",
        "## 1. Tiempos de respuesta del backend", "",
        _leer("tiempos.md"),
        "", "---", "",
        "## 2. Métricas cuantitativas de la IA", "",
        _leer("metricas_ia.md"),
        "", "---", "",
        "## 3. Casos límite (comportamiento honesto)", "",
        _leer("casos_limite.md"),
        "", "---", "",
        "## 3b. Hallazgos y limitaciones detectadas", "",
        _leer("hallazgos.md"),
        "", "---", "",
        "## 4. Casos simulados — resultados obtenidos", "",
        "### Caso 1 — Turmequé", "", _leer("caso1_resumen.md"),
        "", "### Caso 2 — Villavicencio", "", _leer("caso2_resumen.md"),
        "", "### Caso 3 — Turmequé vs Villavicencio", "", _leer("caso3_resumen.md"),
        "", "### Comparativa ambiental", "", _leer("comparativa_ambiental.md"),
        "", "---", "",
        "## 5. Evidencia del ETL diario (DANE/SIPSA)", "",
        _leer("evidencia_etl.md"),
        "", "---", "",
        "## Archivos JSON de respaldo (para figuras)", "",
    ]
    jsons = sorted(f for f in os.listdir(DIR_RESULTADOS) if f.endswith(".json"))
    for j in jsons:
        partes.append(f"- `resultados/{j}`")

    ruta = os.path.join(RAIZ, "RESUMEN_GENERAL.md")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))
    print(f"✅ RESUMEN_GENERAL.md generado en {ruta}")


if __name__ == "__main__":
    main()
