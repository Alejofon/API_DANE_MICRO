# MiSiembra — Resumen general de pruebas de software

- **Backend probado:** https://api-dane-micro.onrender.com
- **Generado:** 2026-07-09 16:07:28

Este archivo consolida todos los resultados de la carpeta `pruebas_validacion/`. Cada sección corresponde a un entregable del plan de pruebas del documento de grado.

---

## 1. Tiempos de respuesta del backend

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

---

## 2. Métricas cuantitativas de la IA

# Métricas cuantitativas de la IA — MiSiembra (2026-07-09 16:00:24)

## Resultados globales

- **Precisión global:** 89.3%
- **Exhaustividad global (recall@5):** 13.9%
- **Tasa de corrección/alucinación IA:** 5.5%

## Detalle por escenario (precisión y recall)

| Zona | Piso | Altitud | $ | Área m² | Recomendados | Precisión | Recall@5 | Apt+viables tabla | IA no verif. |
|---|---|--:|--:|--:|---|--:|--:|--:|--:|
| Turmequé | frío | 2354.0 | 2,000,000 | 10,000 | Yuca para consumo fresco o doble propósito, Hongo ostra (Pleurotus ostreatus) en bolsa sobre residuos agrícolas, Lechuga baby leaf hidropónica en sistema flotante, Albahaca (Ocimum basilicum) para fresco y venta gourmet, Uchuva (Physalis peruviana) en sistema tecnificado | 0.75 | 0.13 | 23 | 1 |
| Villavicencio | cálido | 437.0 | 50,000,000 | 100,000 | Hongo ostra (Pleurotus spp.), Yuca industrial, Hierbabuena (Mentha spicata), Guanábana (cultivar mejorado tipo AGROSAVIA), Albahaca (Ocimum basilicum) bajo manejo tecnificado | 1.0 | 0.133 | 15 | 3 |
| Tocancipá | frío | 2595.0 | 5,000,000 | 5,000 | Tomate cherry bajo invernadero, Orellana (Pleurotus ostreatus) en bolsa, Lechuga crespa en hidroponia NFT, Hierbabuena / menta, Cilantro de corte | 0.667 | 0.091 | 22 | 2 |
| Santa Marta | cálido | 10.0 | 10,000,000 | 2,000 | Seta ostra (Pleurotus spp.) en sala climatizada, Tomate cherry bajo invernadero ventilado, Lechuga hidropónica tipo romana/crespa en sistema NFT bajo invernadero o malla, Hierbabuena (Mentha spicata) intensiva en camas elevadas o macetas, Microgreens gourmet mixtos (rábano, mostaza, girasol, arveja) | 1.0 | 0.133 | 15 | 3 |
| Pasto | frío alto | 2546.0 | 8,000,000 | 8,000 | Mora de Castilla, Romero en seto o cama tecnificada, Lechuga hidropónica tipo batavia/crespa bajo cubierta, Cilantro de corte intensivo, Uchuva | 1.0 | 0.19 | 21 | 1 |
| Armenia | templado | 1472.0 | 15,000,000 | 3,000 | Orellana (Pleurotus ostreatus) en sala climatizada, Follaje y flor de corte de alta densidad en invernadero (alstroemeria, gypsophila o limonium), Microgreens gourmet (rábano, girasol, arveja, mostaza), Lechuga hidropónica tipo NFT bajo cubierta, Fresa bajo cubierta en canaleta o maceta | 0.5 | 0.059 | 17 | 3 |
| Florencia | cálido | 258.0 | 3,000,000 | 10,000 | Yuca industrial para transformación (harina/almidón), Guayaba mejorada para mercado fresco y pulpa, Sacha inchi | 1.0 | 0.067 | 15 | 2 |
| Medellín | templado | 1476.0 | 20,000,000 | 4,000 | Microgreens gourmet mixtos (rábano, mostaza, girasol, arveja), Tomate cherry bajo invernadero, Flor de corte bajo invernadero (crisantemo o clavel estándar), Orellana (Pleurotus ostreatus) en sala controlada, Lechuga hidropónica (sistema NFT o raíz flotante) | 1.0 | 0.118 | 17 | 3 |
| Valledupar | cálido | 169.0 | 8,000,000 | 8,000 | Tomate cherry bajo invernadero o casa malla, Romero (Rosmarinus officinalis), Hierbabuena (Mentha spicata) para fresco, secado y aceites, Forraje verde hidropónico de maiz o cebada, Lechuga hidropónica en sistema protegido o malla sombra | 1.0 | 0.2 | 15 | 2 |
| Chocontá | frío | 2653.0 | 6,000,000 | 6,000 | Lechuga hidropónica tipo baby leaf / cabeza en NFT bajo cubierta, Cilantro de corte, Uchuva, Fresa bajo cubierta, Arveja grano verde con tutorado | 1.0 | 0.25 | 20 | 0 |

## Tasa de error/alucinación (cultivos novedosos → fuerza IA)

| Cultivo | Origen | Campos corregidos | Total | Tasa |
|---|---|--:|--:|--:|
| Espárrago | cache | 0 | 11 | 0% |
| Kale | cache | 0 | 11 | 0% |
| Jengibre | cache | 0 | 11 | 0% |
| Cúrcuma | cache | 1 | 11 | 9% |
| Arándano | cache | 2 | 11 | 18% |

## Definiciones (nota metodológica)

- **Precisión** = cultivos recomendados climáticamente aptos (altitud real vs rango de la tabla curada, `es_apto_por_altitud`) y viables (el motor solo devuelve viables) / total recomendados verificables. Cultivos propuestos por IA fuera de la tabla se cuentan aparte (columna «IA no verif.»).
- **Recall@5** = cultivos de la tabla aptos por altitud Y viables con el presupuesto/área (verificado con `/calculo-directo`) que aparecen entre las 5 opciones devueltas / total de esos cultivos. **Interpretación importante:** esta métrica está acotada estructuralmente por dos factores de diseño, no por un fallo del sistema. (1) La app devuelve solo 5 opciones, pero en promedio hay ~18 cultivos viables por zona → el recall máximo teórico es ~5/18 ≈ 28 %. (2) El sistema prioriza NOVEDAD: varias de las 5 opciones son cultivos propuestos por IA fuera de la tabla curada (columna «IA no verif.»), que por definición no cuentan como «cultivo de la tabla recuperado». Un recall@5 de ~14 % significa que el sistema cubre cerca de la mitad del máximo teórico con cultivos conocidos y usa el resto de los cupos para ideas novedosas — que es el comportamiento buscado.
- **Tasa de alucinación** = campos técnicos numéricos que la validación completó/corrigió con respaldo (`campos_estimados`) / total de campos técnicos, promediado sobre cultivos novedosos que fuerzan la resolución por IA. (En esta corrida los cultivos novedosos salieron de caché de una corrida previa, por eso figuran como `origen=cache`: los valores de corrección son los que la IA produjo originalmente.)

---

## 3. Casos límite (comportamiento honesto)

# Casos límite — comportamiento honesto (2026-07-09 15:46:43)

## (a) Cultivo no apto por clima — Cacao en Turmequé (~2.400 msnm)
- `apto_para_la_zona`: **False**
- Motivo: La zona está a ~2354 msnm, por encima del rango apto de este cultivo (0-1400 msnm). Suele ser demasiado frío/alto para él.
- Tiempo de respuesta: 0.56s (corta sin llamar a la IA)

## (b) Presupuesto insuficiente — $50.000 COP, 100 m² (Tocancipá)
- `sin_opciones_viables`: **True**
- Mensaje: Con el presupuesto y el área indicados no encontramos un cultivo rentable en esta zona. Ajusta el presupuesto o el área e intenta de nuevo.
- Cultivo más cercano: Maíz amarillo criollo para grano/forraje — mínimo ~20 m², $172925 COP

## (c) Terreno grande, poco dinero — Papa, $1.000.000 COP, 500 ha
- Área disponible: 5.000.000 m² (500 ha)
- **Área recomendada: 221 m²** (fracción del terreno que el presupuesto cubre)
- Nivel: Media · Ganancia: $428,830 COP


---

## 3b. Hallazgos y limitaciones detectadas

# Hallazgos de las pruebas (limitaciones detectadas · trabajo futuro)

Las pruebas automatizadas no solo confirmaron el comportamiento esperado;
también expusieron dos limitaciones reales del sistema, útiles para la sección
de discusión / trabajo futuro del documento.

## Hallazgo 1 — Sistemas intensivos disparan ganancias atípicas

En el Caso 2 (Villavicencio, $50.000.000, 10 ha), la primera opción fue
**"Hongo ostra (Pleurotus spp.)" con una ganancia estimada de $8.194.211.687**
(ocho mil millones), claramente irreal.

- **Causa:** los sistemas intensivos (hongos, hidroponía) se modelan expresando
  su costo y rendimiento "por hectárea equivalente" para que el motor los escale.
  Cuando la IA entrega un rendimiento por hectárea muy alto y un precio gourmet,
  el producto de ambos infla la cifra.
- **Lo que SÍ funcionó:** el guardrail del motor marcó el registro con
  `ganancia_atipica = True` (detectó la anomalía).
- **Corrección aplicada:** a raíz de este hallazgo se modificó `/opciones-cultivo`
  para **excluir del listado** los candidatos con `ganancia_atipica = True` (siguen
  accesibles vía `/plan-cultivo` si el usuario los pide directo). Pendiente de
  desplegar y re-medir. Mejora futura adicional: acotar el rendimiento/ha de los
  sistemas intensivos con un tope específico por tipo de sistema.

## Hallazgo 2 — La IA puede proponer cultivos climáticamente marginales

En el Caso 1 y en el escenario de métricas de **Turmequé (2.354 msnm, frío)** el
sistema propuso **"Yuca para consumo fresco"**, un cultivo de tierra cálida
(rango apto 0–1.800 msnm). Esto bajó la **precisión** de esa zona a 0,75.

- **Causa:** el filtro duro de aptitud por altitud
  (`candidatos_por_altitud` / `es_apto_por_altitud`) se aplica a los candidatos
  de la **tabla curada**, pero los candidatos que propone la **IA** no pasan por
  ese filtro determinístico (la IA recibe el contexto de clima en el prompt, pero
  puede equivocarse).
- **Lo que SÍ funcionó:** la métrica de precisión (89,3 % global) detectó y
  cuantificó exactamente estos casos.
- **Corrección aplicada:** a raíz de este hallazgo se modificó `/opciones-cultivo`
  para aplicar `es_apto_por_altitud` **también** a los candidatos propuestos por IA
  (cuando mapean a un cultivo de la tabla), descartando los no aptos antes de
  mostrarlos y registrándolos en `descartados_por_clima`. Se espera que esto lleve
  la precisión cerca del 100 % en la re-medición (pendiente de desplegar).

## Lo que se confirmó correcto

- Corte por clima sin gastar IA: cacao en Turmequé se rechaza en **0,56 s**.
- Presupuesto insuficiente: respuesta honesta `sin_opciones_viables` con el
  mínimo requerido, sin inventar proyectos.
- Terreno grande y poco dinero: se recomienda una **fracción** del terreno
  (221 m² de 500 ha con $1.000.000), no se descarta por no cubrirlo todo.
- Tasa de corrección/alucinación de la IA baja (5,5 %): la mayoría de los
  parámetros técnicos que entrega la IA pasan la validación sin corrección.


---

## 4. Casos simulados — resultados obtenidos

### Caso 1 — Turmequé

## Caso 1 — Turmequé, Boyacá ($2.000.000 · 1 ha · plano)

**Datos de entrada:** presupuesto $2.000.000 COP, área 1 ha (10.000 m²), terreno plano

**Origen de candidatos:** ia_busqueda · **Perfil:** extensivo · **Altitud:** 2354.0 msnm

| # | Cultivo | Rentabilidad | Ganancia (COP) | Área recom. (m²) |
|--:|---|---|--:|--:|
| 1 | Yuca para consumo fresco o doble propósito | Alta | 7,744,516 | 2,534 |
| 2 | Hongo ostra (Pleurotus ostreatus) en bolsa sobre residuos agrícolas | Alta | 7,071,510 | 420 |
| 3 | Lechuga baby leaf hidropónica en sistema flotante | Alta | 2,335,954 | 574 |
| 4 | Albahaca (Ocimum basilicum) para fresco y venta gourmet | Alta | 1,293,769 | 1,098 |
| 5 | Uchuva (Physalis peruviana) en sistema tecnificado | Alta | 1,293,407 | 1,016 |

**Plan detallado ejecutado para:** Yuca para consumo fresco o doble propósito


### Caso 2 — Villavicencio

## Caso 2 — Villavicencio, Meta ($50.000.000 · 10 ha · plano)

**Datos de entrada:** presupuesto $50.000.000 COP, área 10 ha (100.000 m²), terreno plano

**Origen de candidatos:** ia_busqueda · **Perfil:** extensivo · **Altitud:** 437.0 msnm

| # | Cultivo | Rentabilidad | Ganancia (COP) | Área recom. (m²) |
|--:|---|---|--:|--:|
| 1 | Hongo ostra (Pleurotus spp.) | Alta | 8,194,211,687 | 10,992 |
| 2 | Yuca industrial | Alta | 269,193,100 | 68,288 |
| 3 | Hierbabuena (Mentha spicata) | Alta | 208,083,205 | 15,362 |
| 4 | Guanábana (cultivar mejorado tipo AGROSAVIA) | Alta | 73,086,420 | 54,705 |
| 5 | Albahaca (Ocimum basilicum) bajo manejo tecnificado | Alta | 38,753,709 | 29,585 |

### Caso 3 — Turmequé vs Villavicencio

## Caso 3 · Escenario A — Turmequé ($10.000.000 · 2 ha)

**Datos de entrada:** presupuesto $10.000.000 COP, área 2 ha (20.000 m²)

**Origen de candidatos:** cache_ia · **Perfil:** extensivo · **Altitud:** 2354.0 msnm

| # | Cultivo | Rentabilidad | Ganancia (COP) | Área recom. (m²) |
|--:|---|---|--:|--:|
| 1 | Yuca para consumo fresco o doble propósito | Alta | 41,882,964 | 13,493 |
| 2 | Hongo ostra (Pleurotus ostreatus) en bolsa sobre residuos agrícolas | Alta | 38,299,659 | 2,236 |
| 3 | Lechuga baby leaf hidropónica en sistema flotante | Alta | 13,086,026 | 3,054 |
| 4 | Albahaca (Ocimum basilicum) para fresco y venta gourmet | Alta | 7,537,092 | 5,846 |
| 5 | Uchuva (Physalis peruviana) en sistema tecnificado | Alta | 7,535,165 | 5,412 |

## Caso 3 · Escenario B — Villavicencio ($10.000.000 · 2 ha)

**Datos de entrada:** presupuesto $10.000.000 COP, área 2 ha (20.000 m²)

**Origen de candidatos:** cache_ia · **Perfil:** extensivo · **Altitud:** 437.0 msnm

| # | Cultivo | Rentabilidad | Ganancia (COP) | Área recom. (m²) |
|--:|---|---|--:|--:|
| 1 | Hongo ostra (Pleurotus spp.) | Alta | 1,618,996,692 | 2,172 |
| 2 | Yuca industrial | Alta | 53,070,252 | 13,493 |
| 3 | Hierbabuena (Mentha spicata) | Alta | 40,995,378 | 3,035 |
| 4 | Guanábana (cultivar mejorado tipo AGROSAVIA) | Alta | 14,320,988 | 10,809 |
| 5 | Albahaca (Ocimum basilicum) bajo manejo tecnificado | Alta | 7,537,092 | 5,846 |

### Comparativa ambiental

# Comparativa ambiental — 2026-07-09 16:00:17

| Variable | Turmequé (Boyacá) | Villavicencio (Meta) |
|---|--:|--:|
| temperatura_C | 15.5 | 25.3 |
| humedad_% | 88 | 87 |
| precipitacion_mm | 21.2 | 19.0 |
| evapotranspiracion_mm | 1.5 | 2.14 |
| pH | 4.58 | n/d |
| arcilla_% | 29.2 | n/d |
| arena_% | 24.35 | n/d |
| altitud_msnm | 2354.0 | 437.0 |

> Suelo (ISRIC SoilGrids): pH y texturas escalados a unidades reales (pH×10 y g/kg del origen). "n/d" = ISRIC no devolvió dato en ese punto.

---

## 5. Evidencia del ETL diario (DANE/SIPSA)

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

---

## Archivos JSON de respaldo (para figuras)

- `resultados/caso1_analisis.json`
- `resultados/caso1_opciones.json`
- `resultados/caso1_plan.json`
- `resultados/caso2_analisis.json`
- `resultados/caso2_opciones.json`
- `resultados/caso3A_analisis.json`
- `resultados/caso3A_opciones.json`
- `resultados/caso3B_analisis.json`
- `resultados/caso3B_opciones.json`
- `resultados/casoslimite_a_cacao_noapto.json`
- `resultados/casoslimite_b_presupuesto_infimo.json`
- `resultados/casoslimite_c_terreno_grande.json`
- `resultados/comparativa_ambiental.json`
- `resultados/evidencia_etl.json`