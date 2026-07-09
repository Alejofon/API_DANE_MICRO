# Evidencia del ETL DANE/SIPSA — 2026-07-09 15:39:23

- **Registros en `dane_normalizado`:** 674,248
- **Rango de fechas:** 2020-02-01 → **2026-07-08** (fecha máxima)
- **Artículos distintos:** 36
- **Departamentos (centrales mayoristas) distintos:** 21

**Muestra reciente:**

| Artículo | Departamento | Precio/kg (COP) | Fecha |
|---|---|--:|---|
| Tomate | SUCRE | 2650.0 | 2026-07-08 |
| Tomate de árbol | SUCRE | 4650.0 | 2026-07-08 |
| Yuca | SUCRE | 2250.0 | 2026-07-08 |
| Zanahoria | SUCRE | 1906.0 | 2026-07-08 |
| Ahuyama | CESAR | 2300.0 | 2026-07-08 |
| Banano | CESAR | 1417.0 | 2026-07-08 |
| Cebolla cabezona blanca | CESAR | 3867.0 | 2026-07-08 |
| Chócolo mazorca | CESAR | 1767.0 | 2026-07-08 |

> El ETL se ejecuta a diario mediante un workflow de GitHub Actions (`.github/workflows/etl.yml`) que corre `etl.py` contra el SOAP oficial del DANE.