# MiSiembra — Documentación técnica (contexto para Cowork)

Este documento resume cómo funciona internamente MiSiembra tras la reingeniería
del backend y la app. Cubre desde el problema de partida hasta el resultado
actual, describiendo los módulos, las funciones clave, el flujo de datos, la
lógica de viabilidad económica y la versión de pruebas para validación en campo.

---

## 1. Qué es MiSiembra y punto de partida

**Qué es:** app Flutter + backend Flask que recomienda cultivos agrícolas
viables para un agricultor colombiano, dados: ubicación (lat/lon →
departamento/municipio), presupuesto (COP) y área disponible. El valor no es ser
un sistema experto perfecto, sino dar **ideas de negocio agrícola accionables y
explicadas**, apoyadas en datos reales.

**Problema original:** la app llamaba a OpenAI **directamente desde el celular**
(API key embebida en el APK) para pedir nombres de cultivos y un plan en texto
libre. Sin ningún cálculo real detrás, el modelo inventaba cifras económicas sin
sentido. Además, las recomendaciones no filtraban por clima, ni por si el
presupuesto/área alcanzaban para algo rentable.

**Objetivo de la reingeniería:** mover toda la lógica al backend, anclar los
números a fuentes reales, hacer los cálculos en Python (no en la IA) y garantizar
que **solo se recomienden proyectos viables**.

---

## 2. Arquitectura general (flujo)

```
Flutter (app real)
  ├── POST /opciones-cultivo   → propone 5 cultivos rentables para la zona/perfil
  └── POST /plan-cultivo       → plan detallado del cultivo elegido

Flutter (app de pruebas)
  └── POST /calculo-directo    → rentabilidad de UN cultivo específico (validación)

Backend Flask (app.py) — para cualquiera de esos endpoints:
  1. Resuelve PARÁMETROS TÉCNICOS del cultivo:
       tabla curada  →  caché Postgres  →  IA con búsqueda web
  2. Completa/rellena campos faltantes con respaldo por categoría.
  3. Busca el PRECIO DE VENTA real en la tabla DANE/SIPSA (Postgres).
  4. Calcula TODO en Python (calculo_agricola.calcular_plan): costos,
     área financiable, producción, ingreso, ganancia, viabilidad.
  5. (Solo /plan-cultivo) IA redacta el texto explicativo con esas cifras;
     el backend sobrescribe cualquier número que el modelo intente cambiar.
```

Principio rector: **la IA propone IDEAS y redacta texto; nunca calcula números.**
Los números salen de datos curados/oficiales y de matemática en Python.

---

## 3. Fuentes de datos

| Fuente | Qué aporta | Cómo |
|---|---|---|
| **DANE / SIPSA** (tabla `dane_normalizado` en Postgres) | Precio de venta real por kg | `etl.py` descarga el SOAP oficial del DANE y llena la tabla; un GitHub Action (`.github/workflows/etl.yml`) la refresca **a diario, gratis** |
| **Tabla curada** (`tabla_referencia_cultivos.py`) | Parámetros técnicos (costos, densidad, rendimiento, clima) de 39 cultivos | Estática, en código; datos de fichas Agronet/MADR y FINAGRO citadas, o referencia agronómica general marcada como tal |
| **IA con web_search** (`agro_technical_service.py`) | Parámetros de cultivos que NO están en la tabla | OpenAI Responses API restringida a dominios confiables (agrosavia, agronet, ica, upra, fao, fedepapa, etc.) |
| **Caché Postgres** (`cache_tecnico_service.py`) | Reutiliza respuestas de IA por zona | Evita repetir llamadas lentas/costosas |
| **Open-Meteo** (`clima_service.py`) | Clima y **altitud** de la zona | Gratis, sin API key; la altitud verifica aptitud climática |
| **ISRIC SoilGrids** (`soil_service.py`) | Propiedades del suelo | Contexto para la IA |

**Nota geográfica del DANE:** SIPSA solo reporta precios en las ~20 ciudades con
central mayorista propia; `dept_nombre` es el de esa central, no el de la finca.
Por eso `_buscar_precio_dane_para_cultivo` usa una cascada
municipio → departamento → **mercado mayorista de referencia**
(mapa `DEPARTAMENTO_A_MERCADO_DANE`, ej. Cundinamarca → Bogotá/Corabastos) →
nacional, filtrando a los últimos 18 meses.

---

## 4. Backend — módulos y funciones clave

### `app.py` (endpoints y orquestación)
- **`/analisis-terreno`** (GET): consolida clima, suelo, índice de insumos y
  estadísticas de precios DANE por grupo para la zona.
- **`/opciones-cultivo`** (POST): genera las 5 opciones de siembra (ver §5).
- **`/plan-cultivo`** (POST): plan detallado de un cultivo ya elegido (ver §6).
- **`/calculo-directo`** (POST): motor de cálculo puro para la app de pruebas
  (ver §8).
- Helpers:
  - `_buscar_precio_dane_para_cultivo(cultivo, depto, muni)`: precio real DANE
    con cascada geográfica.
  - `_formatear_contexto_clima_suelo(datos_analisis)`: arma texto de contexto
    para la IA.
  - `_temperatura_de_analisis(datos_analisis)`: temperatura media medida (para
    aptitud climática cuando no hay lat/lon).
  - `_bracket_intensidad(presupuesto, area)`: clasifica el perfil en
    `intensivo` / `mixto` / `extensivo` según $/m² (ver §5).

### `services/tabla_referencia_cultivos.py` (tabla curada)
- `TABLA_CULTIVOS`: dict de 39 cultivos por clima (frío, templado, caliente) e
  intensivos (hidroponía, forraje verde hidropónico, hongos, aromáticas). Cada
  entrada trae densidad de siembra, costos por ha, jornales, rendimiento, ciclo,
  **rango de altitud y temperatura**, y la fuente (ficha oficial vs referencia
  general).
- `buscar_en_tabla(nombre)`: match tolerante (sin tildes, sinónimos, por palabra).
- `candidatos_por_altitud(altitud, temperatura)`: lista de cultivos aptos para la
  zona; devuelve `None` si no hay señal climática (para no filtrar a ciegas).
- `es_apto_por_altitud` / `es_apto_por_temperatura`: verdad/falso/None de aptitud.

### `services/cache_tecnico_service.py` (caché en Postgres)
- `asegurar_tabla()`: crea `parametros_cultivo_cache` si no existe (al arrancar).
- `obtener` / `guardar`: parámetros de un cultivo por zona (vigencia 12 meses).
- `obtener_candidatos` / `guardar_candidatos`: set de opciones por zona+perfil;
  además guarda cada candidato individual para que su plan salga instantáneo.

### `services/agro_technical_service.py` (IA de búsqueda)
- `resolver_parametros_tecnicos(cultivo, ...)`: **punto de entrada unificado**.
  Orden: tabla curada → caché → IA. Solo la primera consulta de un cultivo no
  curado en una zona nueva gasta una llamada de IA; se cachea el resultado.
- `obtener_parametros_tecnicos(...)`: llama la Responses API para un cultivo.
- `obtener_candidatos_cultivo(..., presupuesto, area)`: pide a la IA una lista de
  cultivos novedosos apropiados al clima y al perfil presupuesto↔terreno.
- `_describir_perfil_presupuesto_terreno(...)`: inserta en el prompt la
  instrucción de proponer sistemas intensivos vs extensivos según $/m².

### `services/validacion_service.py`
- `validar_parametros(...)`: rechaza cifras técnicamente absurdas (rangos de
  sanidad, costo de material vegetal implícito, etc.).
- `completar_parametros(crudos)`: rellena campos faltantes/inválidos con el
  respaldo genérico de su categoría y reporta cuáles se estimaron. Garantiza que
  el cálculo **nunca** se rompa por un dato faltante.

### `services/calculo_agricola.py` (motor económico — el núcleo)
- `calcular_plan(parametros, presupuesto, area, precio_dane_kg)`: **toda la
  matemática y la decisión de viabilidad** (ver §7).
- `construir_fallback(categoria)` / `construir_candidatos_respaldo()`: respaldos
  genéricos por categoría cuando falla todo lo demás.
- `formatear_resultados_para_ui(...)`: traduce números a strings para Flutter.
- `_clasificar_rentabilidad(ganancia, costo)`: etiqueta Alta/Media/Baja/No viable.

### `services/redaccion_service.py`
- `redactar_plan_final(...)`: pide a gpt-4.1-mini SOLO el texto explicativo,
  reutilizando las cifras ya calculadas (el backend las sobrescribe por seguridad).
- `plan_no_apto(...)`: respuesta corta cuando el cultivo no es apto para la zona.

### `services/clima_service.py`
- `get_climate_data(lat, lon)`: temperatura, humedad, precipitación (Open-Meteo).
- `get_elevation(lat, lon)`: altitud en msnm (para aptitud climática real).

---

## 5. Flujo de `/opciones-cultivo` (las 5 opciones)

Idea clave: **la IA genera las ideas** (novedad) y **la tabla aporta números
confiables** cuando el cultivo está en ella. La tabla NO limita qué se propone.

1. Se calcula el **perfil de intensidad** con `_bracket_intensidad` (según $/m²):
   - `intensivo` (≥ $5.000/m²): poca área, buen presupuesto → hidroponía,
     invernadero, forraje verde hidropónico, gourmet.
   - `extensivo` (≤ $500/m²): mucha área, poco dinero → cultivos de bajo insumo.
   - `mixto`: intermedio.
2. Se buscan candidatos en la **caché** por zona+perfil. Si no hay, se piden a la
   **IA** (`obtener_candidatos_cultivo`, consciente del perfil) y se cachean. La
   primera vez tarda ~1-2 min; las siguientes son instantáneas.
3. Para cada candidato: si está en la tabla curada se usan **sus** números; si
   no, los de la IA. Se completan huecos con `completar_parametros`.
4. Se calcula la rentabilidad real de cada uno con `calcular_plan` (precio DANE).
5. **Filtro de viabilidad:** se descartan los "No viable" o con ganancia ≤ 0. Se
   ordenan por ganancia y se devuelven los 5 mejores.
6. Si la IA falla, se cae a la tabla curada filtrada por clima. Si nada es
   viable, se devuelve `sin_opciones_viables: true` con un mensaje honesto y el
   mínimo requerido (no se inventa un proyecto).

---

## 6. Flujo de `/plan-cultivo` (plan detallado)

1. **Aptitud climática con altitud real:** si el cultivo está en la tabla y su
   rango de altitud (o temperatura) no cuadra con la zona, se corta de una
   (`plan_no_apto`) sin gastar IA. Ej.: cacao a 2.600 msnm → no apto.
2. Parámetros técnicos vía `resolver_parametros_tecnicos` (tabla → caché → IA).
3. `completar_parametros` rellena lo que falte.
4. `_buscar_precio_dane_para_cultivo` obtiene el precio real.
5. `calcular_plan` hace toda la matemática.
6. `redactar_plan_final` escribe el texto; el backend sobrescribe los números.

Devuelve el mismo esquema JSON que la app espera (parsing/UI/historial intactos).

---

## 7. Lógica de viabilidad (el cambio más importante)

Antes, la app marcaba casi todo como "No viable" porque exigía cubrir escalas de
área fijas por categoría (75 m² / 350 m² / 5.000 m² / 1 ha). Se reemplazó por
**economía real** en `calcular_plan`:

1. **Filtro de clima** (altitud/temperatura) — hecho antes del cálculo.
2. **Margen por hectárea:** `ingreso_por_ha − costo_variable_por_ha`. Si es ≤ 0,
   el cultivo pierde a cualquier escala → inviable (no cubre ni costos variables).
3. **Escala mínima rentable = punto de equilibrio**
   (`costo_fijo / margen_por_ha`), acotada por un piso absoluto de sanidad
   (20 m²). Ya no es un piso arbitrario por categoría, sale de la economía real
   del cultivo.
4. **La tierra es un TOPE, no un requisito:** se puede usar menos de la
   disponible. Se recomienda `min(área que paga el presupuesto, área disponible)`.
   Ej.: con 500 ha y $1M, se recomienda la porción que el dinero cubre
   ("siembra 582 m² de tus 500 ha"), no se descarta por no cubrirlo todo.
5. **Costo fijo absoluto ($150.000):** antes era el 10% del costo/ha, que
   explotaba en cultivos caros y bloqueaba a agricultores con poco presupuesto
   aunque pudieran sembrar una parcela pequeña rentable.
6. Un proyecto es **viable** solo si: hay datos de rendimiento/precio, el margen
   es positivo, la escala mínima cabe en el terreno y el presupuesto la paga, y
   la ganancia final es > 0.

Salida de `calcular_plan`: costos por ha, área recomendada, número de plantas,
producción, ingreso, ganancia, nivel de rentabilidad, motivo (si no es viable),
retorno de inversión por ciclos, área mínima rentable y presupuesto mínimo.

---

## 8. App de pruebas / validación (rama `pruebas-validacion`)

Necesidad: para medir la efectividad de las recomendaciones ante agricultores
experimentados, hace falta pedir un **cultivo específico** con presupuesto/área
conocidos y comparar la rentabilidad de la app con la realidad — usando el mismo
motor de cálculo.

- **Backend — `/calculo-directo`** (POST): recibe cultivo + presupuesto + área +
  ubicación y devuelve la rentabilidad con **exactamente el mismo `calcular_plan`**
  que la app real (tabla → caché → IA, precio DANE), pero **sin la redacción por
  IA** (más rápido/barato para campo). No rechaza por clima (el agricultor ya lo
  cultiva); la aptitud se reporta como dato. Devuelve los números crudos y los
  parámetros técnicos usados para poder contrastar cada cifra.
- **Flutter — rama `pruebas-validacion`:**
  - `TestCalculoPage` (`lib/screens/test_calculo_page.dart`): formulario
    (cultivo, departamento, municipio, presupuesto, área) → llama
    `/calculo-directo` → muestra nivel, ganancia, ingreso, costo, área
    recomendada, producción, precio usado y su fuente, área mínima rentable, y
    (desplegable) los parámetros técnicos.
  - `main.dart` arranca en esa pantalla.
  - `applicationId = com.example.misiembra_v0.pruebas` y label "MiSiembra
    Pruebas": se instala como **app separada** junto a la real en el mismo
    teléfono.
- **Dos APK:** se compilan del mismo proyecto cambiando de rama
  (`git checkout main` → app real; `git checkout pruebas-validacion` → app de
  pruebas), con `flutter build apk --release`.

---

## 9. Cambios en la app Flutter (rama `main`)

- `options_page.dart` y `project_detail_page.dart`: ya no llaman a OpenAI;
  llaman a `/opciones-cultivo` y `/plan-cultivo`. Ahora también envían `lat`/`lon`
  para la verificación de aptitud climática.
- `snackbar_utils.dart` (`showTopSnackBar`): las notificaciones se movieron a la
  parte **superior** de la pantalla. Antes usaban un `SnackBar` flotante que
  Flutter ancla siempre abajo y tapaba los botones; ahora es un toast propio
  basado en `Overlay`, con animación y auto-cierre.

---

## 10. Despliegue y configuración

- Variables de entorno del backend (Render): `OPENAI_API_KEY` (solo backend,
  nunca en Flutter), `DATABASE_URL` (Postgres).
- Comando de arranque: `gunicorn app:app --timeout 300 --workers 2` (la búsqueda
  con IA puede tardar).
- La tabla de caché se crea sola al arrancar (`asegurar_tabla`).
- El refresco de precios DANE corre solo a diario (GitHub Action).

---

## 11. Limitaciones conocidas (honestas)

- El ranking de opciones es por ganancia absoluta por ciclo, que mezcla
  horizontes temporales (un frutal de 3 años puede quedar sobre una hortaliza de
  2 meses). Mejora futura: normalizar por mes.
- Cultivos sin registro en DANE (ej. quinua) usan un precio genérico de respaldo
  que puede subestimar su rentabilidad. Es un vacío de datos, no de lógica.
- Parte de la tabla curada (sobre todo clima frío y algunos de tierra caliente)
  usa "referencia agronómica general", no ficha oficial citada. El precio de
  venta, que es lo que más pesa, siempre es DANE real.
- No hay pruebas automatizadas; la validación fue manual contra el Postgres real.
```
