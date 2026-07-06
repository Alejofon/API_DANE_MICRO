import requests

BASE_URL = "https://api.open-meteo.com/v1/forecast"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


def get_elevation(lat, lon):
    """
    Elevación (msnm) para lat/lon vía Open-Meteo (mismo proveedor que el
    clima, gratis, sin API key). Se usa para verificar aptitud climática de
    un cultivo por rango de altitud sin depender de que la IA "adivine" el
    piso térmico de la zona.
    """
    try:
        response = requests.get(
            ELEVATION_URL,
            params={"latitude": lat, "longitude": lon},
            timeout=15,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        elevaciones = data.get("elevation")
        if isinstance(elevaciones, list) and elevaciones:
            return float(elevaciones[0])
        return None
    except Exception:
        return None


def get_climate_data(lat, lon):

    params = {
        "latitude": lat,
        "longitude": lon,

        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m"
        ],

        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "et0_fao_evapotranspiration"
        ],

        "timezone": "auto",
        "forecast_days": 1
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        return None

    data = response.json()

    try:

        return {

            "current": {
                "temperature": data["current"].get("temperature_2m"),
                "humidity": data["current"].get("relative_humidity_2m"),
                "precipitation": data["current"].get("precipitation"),
                "wind_speed": data["current"].get("wind_speed_10m")
            },

            "daily": {
                "temperature_max": data["daily"]["temperature_2m_max"][0],
                "temperature_min": data["daily"]["temperature_2m_min"][0],
                "precipitation_sum": data["daily"]["precipitation_sum"][0],
                "evapotranspiration": data["daily"]["et0_fao_evapotranspiration"][0]
            }

        }

    except Exception:
        return None
    