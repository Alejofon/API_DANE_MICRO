import requests
from xml.etree import ElementTree as ET

WCS_BASE_URL = "https://maps.isric.org/mapserv"

SOIL_LAYERS = {
    "ph": {
        "map": "/map/phh2o.map",
        "coverage": "phh2o_0-5cm_mean"
    },
    "clay": {
        "map": "/map/clay.map",
        "coverage": "clay_0-5cm_mean"
    },
    "sand": {
        "map": "/map/sand.map",
        "coverage": "sand_0-5cm_mean"
    }
}


def get_single_soil_value(lat, lon, map_file, coverage_id):

    params = {
        "map": map_file,
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "COVERAGEID": coverage_id,
        "SUBSET": [
            f"long({lon},{lon})",
            f"lat({lat},{lat})"
        ],
        "FORMAT": "text/xml"
    }

    response = requests.get(
        WCS_BASE_URL,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        return None

    try:

        root = ET.fromstring(response.text)

        text_content = "".join(root.itertext())

        numbers = [
            float(x)
            for x in text_content.replace(",", " ").split()
            if x.replace(".", "", 1).replace("-", "", 1).isdigit()
        ]

        if numbers:
            return numbers[-1]

        return None

    except Exception:
        return None


def get_soil_data(lat, lon):

    results = {}

    for key, config in SOIL_LAYERS.items():

        value = get_single_soil_value(
            lat=lat,
            lon=lon,
            map_file=config["map"],
            coverage_id=config["coverage"]
        )

        results[key] = value

    return results