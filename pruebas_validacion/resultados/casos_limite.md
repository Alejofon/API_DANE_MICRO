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
