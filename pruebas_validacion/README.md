# pruebas_validacion/ — Instrumentación de pruebas de MiSiembra

Scripts para medir y evidenciar el comportamiento del backend de MiSiembra, de
cara al plan de pruebas del proyecto de grado. **No modifican el backend**: solo
lo consultan (por defecto, el despliegue en Render).

## Requisitos
```bash
source ../venv/bin/activate        # o ../.venv
pip install requests psycopg2-binary python-dotenv   # ya están en el proyecto
```
El backend por defecto es `https://api-dane-micro.onrender.com`. Para probar
contra otro (ej. local), exporta `PRUEBAS_BASE_URL`:
```bash
export PRUEBAS_BASE_URL=http://localhost:5000
```

## Scripts
| Script | Qué mide / produce | Usa IA (costo) |
|---|---|:--:|
| `benchmark_tiempos.py` | Tiempos de respuesta (avg/min/max/p95) por endpoint → `tiempos.csv`, `tiempos.md` | parcial |
| `casos_simulados.py` | Re-ejecuta los 3 casos del documento, guarda JSON + resúmenes + comparativa ambiental | sí |
| `metricas_ia.py` | Precisión, recall@5 y tasa de alucinación → `metricas_ia.csv`, `metricas_ia.md` | sí |
| `casos_limite.py` | No apto por clima / presupuesto insuficiente / terreno grande → `casos_limite.md` | parcial |
| `evidencia_etl.py` | Conteo y fecha máx de `dane_normalizado` (requiere `DATABASE_URL`) → `evidencia_etl.md` | no |
| `generar_resumen.py` | Consolida todo en `RESUMEN_GENERAL.md` | no |

## Ejecución completa
```bash
python3 benchmark_tiempos.py --reps 10
python3 casos_simulados.py
python3 casos_limite.py
python3 metricas_ia.py
python3 evidencia_etl.py
python3 generar_resumen.py
```
Los resultados quedan en `resultados/`. Si Render está dormido (plan gratuito),
el primer request tarda ~1 min (arranque en frío) y se descarta de las medidas.

`escenarios.json` es editable: define las zonas/presupuestos/áreas del lote de
`metricas_ia.py`.
