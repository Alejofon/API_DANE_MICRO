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

    delta = 0.01

    min_lon = lon - delta
    max_lon = lon + delta

    min_lat = lat - delta
    max_lat = lat + delta

    params = [
        ("map", map_file),
        ("SERVICE", "WCS"),
        ("VERSION", "2.0.1"),
        ("REQUEST", "GetCoverage"),
        ("COVERAGEID", coverage_id),
        ("FORMAT", "image/tiff"),
        ("SUBSETTINGCRS", "http://www.opengis.net/def/crs/EPSG/0/4326"),
        ("OUTPUTCRS", "http://www.opengis.net/def/crs/EPSG/0/4326"),
        ("SUBSET", f"Lon({min_lon},{max_lon})"),
        ("SUBSET", f"Lat({min_lat},{max_lat})")
    ]

    response = requests.get(WCS_BASE_URL, params=params, timeout=60)
    print(response.url)
    print(response.status_code)
    print(response.text[:500])

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