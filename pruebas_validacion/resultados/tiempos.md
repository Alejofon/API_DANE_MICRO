# Tiempos de respuesta del backend — MiSiembra

- **Backend:** https://api-dane-micro.onrender.com
- **Fecha de ejecución:** 2026-07-09 15:44:31
- **Repeticiones (deterministas):** 8

| Endpoint | IA | Reps | OK | Promedio (ms) | Mín (ms) | Máx (ms) | P95 (ms) |
|---|:--:|:--:|:--:|--:|--:|--:|--:|
| /analisis-terreno | No | 8 | 8 | 2373.7 | 2042.3 | 3014.4 | 3014.4 |
| /opciones-cultivo (zona nueva, IA) | Sí | 1 | 1 | 55000.4 | 55000.4 | 55000.4 | 55000.4 |
| /opciones-cultivo (con caché) | No | 8 | 8 | 4276.4 | 4197.8 | 4330.0 | 4330.0 |
| /plan-cultivo (apto) | Sí | 4 | 4 | 26654.7 | 23582.9 | 32916.9 | 32916.9 |
| /plan-cultivo (no apto) | No | 8 | 8 | 573.0 | 541.1 | 657.2 | 657.2 |
| /calculo-directo | No | 8 | 8 | 385.0 | 348.7 | 472.4 | 472.4 |
| /buscar-insumos | No | 4 | 4 | 601.4 | 566.1 | 625.8 | 625.8 |

> Nota: los endpoints marcados con IA dependen de OpenAI (búsqueda web y/o redacción) y de la latencia variable de la red; sus tiempos no son comparables con los deterministas. La primera consulta de una zona por `/opciones-cultivo` pasa por búsqueda IA (minutos); las siguientes salen de caché en Postgres (milisegundos). El primer request tras inactividad incluye el arranque en frío de Render (plan gratuito) y se descartó del muestreo.