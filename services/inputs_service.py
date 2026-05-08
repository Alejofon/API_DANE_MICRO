import requests

BASE_URL = "https://www.datos.gov.co/resource/gwbi-fnzs.json"


def get_inputs_data(limit=20):

    params = {
        "$limit": limit
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        print(response.text)
        return None

    data = response.json()

    results = []

    for item in data:

        results.append(item)

    return results