# services/utils_numeros.py
"""
Utilidades numéricas puras (sin llamadas externas).
Se encargan de convertir los strings que llegan desde Flutter
(presupuesto con puntos de miles, área en distintas unidades)
en números que el resto del backend pueda usar para calcular.
"""

# Conversión de cada unidad de medida usada en el HomePage de Flutter a m².
# NOTA: "Fanegada" no es una unidad estándar en Colombia (varía por región,
# entre ~6.400 y ~10.000 m² según el departamento). Se usa 6.400 m² como
# valor de referencia (el más común en Cundinamarca/Boyacá, zona objetivo
# inicial del proyecto). Si el proyecto se usa en otras regiones, este
# valor debe ajustarse aquí.
AREA_A_M2 = {
    "metros cuadrados": 1.0,
    "hectáreas": 10000.0,
    "hectareas": 10000.0,
    "fanegadas": 6400.0,
    "acres": 4046.8564224,
    "kilómetros cuadrados": 1_000_000.0,
    "kilometros cuadrados": 1_000_000.0,
}


def parsear_numero(valor, default=0.0):
    """
    Convierte un string proveniente de Flutter (con puntos de miles,
    ej: '1.500.000') en un float. Tolera que ya venga como número.
    """
    if valor is None:
        return default
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return default
    # Los TextField de Flutter solo permiten dígitos + el punto de miles
    # que agrega formatNumberWithDots, así que es seguro remover puntos.
    texto = texto.replace(".", "").replace(",", "").strip()
    try:
        return float(texto)
    except ValueError:
        return default


def area_a_m2(area_valor, unidad):
    """
    Convierte el área reportada por el agricultor a metros cuadrados.
    `unidad` debe ser uno de los strings usados en HomePage
    (ej: 'Hectáreas', 'Metros cuadrados', etc). No es sensible a mayúsculas.
    """
    area_num = parsear_numero(area_valor)
    factor = AREA_A_M2.get((unidad or "").strip().lower())
    if factor is None:
        # Unidad desconocida: se asume metros cuadrados para no inflar
        # ni reducir artificialmente el área disponible.
        factor = 1.0
    return area_num * factor


def formatear_cop(valor):
    """Formatea un número como texto de pesos colombianos con puntos de miles."""
    try:
        return "${:,.0f} COP".format(float(valor)).replace(",", ".")
    except (TypeError, ValueError):
        return "No disponible"