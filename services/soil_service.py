import requests
import tempfile
import rasterio

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

    delta = 0.001

    min_lon = lon - delta
    max_lon = lon + delta

    min_lat = lat - delta
    max_lat = lat + delta

    params = {
        "map": map_file,
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "COVERAGEID": coverage_id,
        "FORMAT": "GEOTIFF_FLOAT32",
        "SUBSET": [
            f"long({min_lon},{max_lon})",
            f"lat({min_lat},{max_lat})"
        ]
    }

    response = requests.get(
        WCS_BASE_URL,
        params=params,
        timeout=60
    )

    if response.status_code != 200:
        print("STATUS ERROR:", response.status_code)
        return None

    try:

        with tempfile.NamedTemporaryFile(suffix=".tif") as tmp:

            tmp.write(response.content)
            tmp.flush()

            with rasterio.open(tmp.name) as dataset:

                band = dataset.read(1)

                value = float(band.mean())

                if value < -9990:
                    return None

                return round(value, 2)

    except Exception as e:

        print("SOIL ERROR:", str(e))
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