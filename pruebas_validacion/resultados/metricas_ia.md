# Métricas cuantitativas de la IA — MiSiembra (2026-07-09 16:25:54)

## Resultados globales

- **Precisión global:** 100.0%
- **Exhaustividad global (recall@5):** 17.2%
- **Tasa de corrección/alucinación IA:** 5.5%

## Detalle por escenario (precisión y recall)

| Zona | Piso | Altitud | $ | Área m² | Recomendados | Precisión | Recall@5 | Apt+viables tabla | IA no verif. |
|---|---|--:|--:|--:|---|--:|--:|--:|--:|
| Turmequé | frío | 2354.0 | 2,000,000 | 10,000 | Hongo ostra (Pleurotus ostreatus) en bolsa sobre residuos agrícolas, Lechuga baby leaf hidropónica en sistema flotante, Albahaca (Ocimum basilicum) para fresco y venta gourmet, Uchuva (Physalis peruviana) en sistema tecnificado, Fresa bajo macrotúnel o cubierta liviana | 1.0 | 0.174 | 23 | 1 |
| Villavicencio | cálido | 437.0 | 50,000,000 | 100,000 | Yuca industrial, Hierbabuena (Mentha spicata), Guanábana (cultivar mejorado tipo AGROSAVIA), Albahaca (Ocimum basilicum) bajo manejo tecnificado | 1.0 | 0.133 | 15 | 2 |
| Tocancipá | frío | 2595.0 | 5,000,000 | 5,000 | Lechuga crespa en hidroponia NFT, Hierbabuena / menta, Cilantro de corte, Albahaca aromatica, Fresa tecnificada en mesa o sustrato | 1.0 | 0.182 | 22 | 1 |
| Santa Marta | cálido | 10.0 | 10,000,000 | 2,000 | Lechuga hidropónica tipo romana/crespa en sistema NFT bajo invernadero o malla, Hierbabuena (Mentha spicata) intensiva en camas elevadas o macetas, Microgreens gourmet mixtos (rábano, mostaza, girasol, arveja), Albahaca genovesa/culinaria bajo malla sombra o hidroponía | 1.0 | 0.133 | 15 | 2 |
| Pasto | frío alto | 2546.0 | 8,000,000 | 8,000 | Mora de Castilla, Romero en seto o cama tecnificada, Lechuga hidropónica tipo batavia/crespa bajo cubierta, Cilantro de corte intensivo, Uchuva | 1.0 | 0.19 | 21 | 1 |
| Armenia | templado | 1472.0 | 15,000,000 | 3,000 | Lechuga hidropónica tipo NFT bajo cubierta, Albahaca fresca gourmet en invernadero, Cilantro de corte fino en ambiente protegido | 1.0 | 0.176 | 17 | 0 |
| Florencia | cálido | 258.0 | 3,000,000 | 10,000 | Yuca industrial para transformación (harina/almidón), Guayaba mejorada para mercado fresco y pulpa, Sacha inchi | 1.0 | 0.067 | 15 | 2 |
| Medellín | templado | 1476.0 | 20,000,000 | 4,000 | Flor de corte bajo invernadero (crisantemo o clavel estándar), Orellana (Pleurotus ostreatus) en sala controlada, Lechuga hidropónica (sistema NFT o raíz flotante), Albahaca aromática en hidroponía o sustrato protegido | 1.0 | 0.118 | 17 | 2 |
| Valledupar | cálido | 169.0 | 8,000,000 | 8,000 | Hierbabuena (Mentha spicata) para fresco, secado y aceites, Forraje verde hidropónico de maiz o cebada, Lechuga hidropónica en sistema protegido o malla sombra, Maracuya (Passiflora edulis), Albahaca (Ocimum basilicum) para fresco y coproductos | 1.0 | 0.267 | 15 | 1 |
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
- **Recall@5** = cultivos de la tabla aptos por altitud Y viables con el presupuesto/área (verificado con `/calculo-directo`) que aparecen entre las 5 opciones devueltas / total de esos cultivos. **Interpretación:** está acotado estructuralmente por diseño, no por un fallo: (1) la app devuelve solo 5 opciones pero hay ~18 cultivos viables por zona en promedio → recall máximo teórico ~5/18 ≈ 28 %; (2) el sistema prioriza NOVEDAD, así que varias de las 5 opciones son cultivos propuestos por IA fuera de la tabla (columna «IA no verif.»), que no cuentan como «cultivo de tabla recuperado».
- **Tasa de alucinación** = campos técnicos numéricos que la validación completó/corrigió con respaldo (`campos_estimados`) / total de campos técnicos, promediado sobre cultivos novedosos que fuerzan la resolución por IA.