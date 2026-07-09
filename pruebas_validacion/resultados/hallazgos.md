# Hallazgos de las pruebas (limitaciones detectadas y corregidas)

Las pruebas automatizadas no solo confirmaron el comportamiento esperado;
también expusieron dos limitaciones reales del sistema. Ambas se **corrigieron**
y se **re-midió**, con mejora comprobada — un ciclo detección → corrección →
verificación útil para la sección de resultados/discusión del documento.

> **Antes de las correcciones:** precisión global = **89,3 %**; el Caso 2
> (Villavicencio) mostraba como primera opción "Hongo ostra" con una ganancia
> irreal de **$8.194.211.687**.
> **Después de las correcciones (re-medición):** precisión global = **100,0 %**;
> el Caso 2 ya no muestra la opción de ganancia atípica y encabeza con "Yuca
> industrial" ($269.193.100). La tasa de alucinación de la IA se mantuvo en 5,5 %
> y el recall@5 subió de 13,9 % a 17,2 %.

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
- **Corrección aplicada y verificada:** se modificó `/opciones-cultivo` para
  **excluir del listado** los candidatos con `ganancia_atipica = True` (siguen
  accesibles vía `/plan-cultivo` si el usuario los pide directo). Re-medición: el
  Caso 2 ya no muestra el hongo ostra de $8.194 M. Mejora futura adicional: acotar
  el rendimiento/ha de los sistemas intensivos con un tope por tipo de sistema.

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
- **Corrección aplicada y verificada:** se modificó `/opciones-cultivo` para
  aplicar `es_apto_por_altitud` **también** a los candidatos propuestos por IA
  (cuando mapean a un cultivo de la tabla), descartando los no aptos antes de
  mostrarlos y registrándolos en `descartados_por_clima`. Re-medición: en Turmequé
  "Yuca" aparece ahora en `descartados_por_clima` y la **precisión global subió de
  89,3 % a 100,0 %**.

## Lo que se confirmó correcto

- Corte por clima sin gastar IA: cacao en Turmequé se rechaza en **0,56 s**.
- Presupuesto insuficiente: respuesta honesta `sin_opciones_viables` con el
  mínimo requerido, sin inventar proyectos.
- Terreno grande y poco dinero: se recomienda una **fracción** del terreno
  (221 m² de 500 ha con $1.000.000), no se descarta por no cubrirlo todo.
- Tasa de corrección/alucinación de la IA baja (5,5 %): la mayoría de los
  parámetros técnicos que entrega la IA pasan la validación sin corrección.
