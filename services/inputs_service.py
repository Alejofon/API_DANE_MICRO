import requests

BASE_URL = "https://www.datos.gov.co/resource/gwbi-fnzs.json"


def get_inputs_data(limit=20):

    params = {
        "$limit": limit,
        "$order": "a_o DESC"
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        return None

    data = response.json()

    results = []

    for item in data:

        results.append({

            "producto": item.get("producto"),
            "categoria": item.get("subgrupo"),
            "precio": item.get("precio_promedio"),
            "departamento": item.get("departamento"),
            "municipio": item.get("municipio"),
            "fecha": item.get("a_o")

        })

    return results