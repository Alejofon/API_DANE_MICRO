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