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
- **Lo que falta (trabajo futuro):** el ordenamiento de `/opciones-cultivo` es por
  ganancia absoluta y **no** usa esa bandera, así que la opción atípica quedó de
  primera. Recomendación: en el ranking, filtrar o penalizar los candidatos con
  `ganancia_atipica = True`, o acotar el rendimiento/ha de los sistemas
  intensivos con un tope específico por tipo de sistema.

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
- **Lo que falta (trabajo futuro):** aplicar la verificación `es_apto_por_altitud`
  también a los candidatos propuestos por IA (cuando el cultivo exista en la
  tabla o declare su rango), descartando los no aptos antes de mostrarlos. Esto
  llevaría la precisión cerca del 100 %.

## Lo que se confirmó correcto

- Corte por clima sin gastar IA: cacao en Turmequé se rechaza en **0,56 s**.
- Presupuesto insuficiente: respuesta honesta `sin_opciones_viables` con el
  mínimo requerido, sin inventar proyectos.
- Terreno grande y poco dinero: se recomienda una **fracción** del terreno
  (221 m² de 500 ha con $1.000.000), no se descarta por no cubrirlo todo.
- Tasa de corrección/alucinación de la IA baja (5,5 %): la mayoría de los
  parámetros técnicos que entrega la IA pasan la validación sin corrección.
