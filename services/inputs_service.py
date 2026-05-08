import requests

BASE_URL = "https://www.datos.gov.co/resource/gwbi-fnzs.json"


DATA_CONTEXT = {
    "titulo": "Índice de precios de insumos agrícolas",
    "descripcion": (
        "Índice que resume el comportamiento de los precios en el mercado minorista a nivel nacional "
        "de los productos más utilizados en la actividad agrícola para diferentes etapas de producción."
    ),
    "base_periodo": "Enero de 2021 = 100",
    "alcance": "Nacional",
    "proposito": "Apoyo en la toma de decisiones por parte de los actores del sector agrícola.",
    "categorias": [
        "fertilizantes",
        "plaguicidas",
        "otros insumos"
    ],
    "subcategorias": [
        "simples",
        "compuestos",
        "herbicidas",
        "fungicidas",
        "insecticidas",
        "coadyuvantes",
        "reguladores fisiológicos",
        "molusquicidas"
    ],
    "cambios_metodologicos": [
        "A partir de enero de 2024 se amplía la canasta de productos del índice.",
        "No se incluyen productos con ingrediente activo Clorpirifos, por la Resolución 06365 de 2023 del ICA.",
        "Desde septiembre de 2024 no se incluyen productos con ingrediente activo Fipronil, por la Resolución 0740 de 2023 del ICA."
    ],
    "nota_importante": (
        "Los valores representan un índice, no precios absolutos. "
        "Un valor de 100 equivale al nivel de enero de 2021."
    )
}


FIELD_MAP = {
    "fecha": "fecha",
    "indice_total": "indice_total",
    "total_fertilizantes": "total_fertilizantes",
    "total_plaguicidas": "total_plaguicidas",
    "total_otros": "total_otros",
    "total_simples": "total_simples",
    "total_compuestos": "total_compuestos",
    "total_herbicidas": "total_herbicidas",
    "total_fungicidas": "total_fungicidas",
    "total_insecticidas": "total_insecticidas",
    "urea_46": "urea_46",
    "urea_sulfato": "urea_sulfato",
    "dap_18_46": "dap_18_46",
    "kcl_0_0_60": "kcl_0_0_60",
    "sam": "sam",
    "_15_15_15": "15_15_15",
    "_25_4_24": "25_4_24",
    "_17_6_18_2": "17_6_18_2",
    "_18_18_18": "18_18_18",
    "_31_8_8": "31_8_8",
    "_12_24_12": "12_24_12",
    "_13_26_6": "13_26_6",
    "_15_4_23": "15_4_23",
    "_10_20_30": "10_20_30",
    "_28_4_0_6": "28_4_0_6",
    "glifosato": "glifosato",
    "paraquat": "paraquat",
    "propanil": "propanil",
    "_2_4_d_picloram": "2_4_d_picloram",
    "_2_4_d": "2_4_d",
    "aminopiralid_2_4_d": "aminopiralid_2_4_d",
    "diuron": "diuron",
    "glufosinato_de_amonio": "glufosinato_de_amonio",
    "picloram": "picloram",
    "oxadiazon": "oxadiazon",
    "metsulfuron_metil": "metsulfuron_metil",
    "pendimetalin": "pendimetalin",
    "clorotalonil": "clorotalonil",
    "difenoconazol": "difenoconazol",
    "mancozeb": "mancozeb",
    "mancozeb_cimoxanil": "mancozeb_cimoxanil",
    "azoxistrobin_difenoconazol": "azoxistrobin_difenoconazol",
    "dimetomorf": "dimetomorf",
    "tebuconazol_trifloxistrobin": "tebuconazol_trifloxistrobin",
    "propineb_fluopicolide": "propineb_fluopicolide",
    "mancozeb_metalaxil_m": "mancozeb_metalaxil_m",
    "clorpirifos": "clorpirifos",
    "fipronil": "fipronil",
    "metomil": "metomil",
    "tiametoxam_lambdacihalotrina": "tiametoxam_lambdacihalotrina",
    "abamectina": "abamectina",
    "imidacloprid": "imidacloprid",
    "profenofos_cipermetrina": "profenofos_cipermetrina",
    "cipermetrina": "cipermetrina",
    "profenofos": "profenofos",
    "total_coadyuvantes": "total_coadyuvantes",
    "total_reguladores": "total_reguladores",
    "total_molusquicidas": "total_molusquicidas"
}


def to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def normalize_record(record):
    normalized = {}

    for raw_key, public_key in FIELD_MAP.items():
        if raw_key not in record:
            continue

        value = record.get(raw_key)

        if raw_key == "fecha":
            normalized[public_key] = value
        else:
            normalized[public_key] = to_float(value)

    return normalized


def build_highlights(data):
    highlights = {}

    for key in [
        "indice_total",
        "total_fertilizantes",
        "total_plaguicidas",
        "total_otros",
        "total_simples",
        "total_compuestos",
        "total_herbicidas",
        "total_fungicidas",
        "total_insecticidas"
    ]:
        if key in data:
            highlights[key] = data[key]

    return highlights


def get_inputs_index(limit=1):
    params = {
        "$limit": limit
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        return None

    payload = response.json()

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = [payload]
    else:
        return None

    if not records:
        return None

    latest_record = records[0]
    normalized_data = normalize_record(latest_record)

    return {
        "context": DATA_CONTEXT,
        "data": normalized_data,
        "highlights": build_highlights(normalized_data),
        "raw": latest_record
    }