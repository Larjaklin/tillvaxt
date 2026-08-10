"""Skapa Leaflet-kompatibel GeoJSON för Västra Götalands kommuner.

Swemaps levererar koordinaterna som latitud och longitud. Ingen
koordinatomvandling ska därför göras.
"""

import json
from pathlib import Path

VG_CODES = {
    "1401",
    "1402",
    "1407",
    "1415",
    "1419",
    "1421",
    "1427",
    "1430",
    "1435",
    "1438",
    "1439",
    "1440",
    "1441",
    "1442",
    "1443",
    "1444",
    "1445",
    "1446",
    "1447",
    "1452",
    "1460",
    "1461",
    "1462",
    "1463",
    "1465",
    "1466",
    "1470",
    "1471",
    "1472",
    "1473",
    "1480",
    "1481",
    "1482",
    "1484",
    "1485",
    "1486",
    "1487",
    "1488",
    "1489",
    "1490",
    "1491",
    "1492",
    "1493",
    "1494",
    "1495",
    "1496",
    "1497",
    "1498",
    "1499",
}


def main() -> None:
    import swemaps

    geojson = swemaps.GeoJSONMaps().municipalities()
    selected_features = []

    for feature in geojson["features"]:
        properties = feature.get("properties", {})

        municipality_code = str(
            properties.get("kommunkod")
            or properties.get("KnKod")
            or properties.get("code")
            or ""
        )[-4:]

        if municipality_code not in VG_CODES:
            continue

        properties.setdefault(
            "kommunkod",
            municipality_code,
        )

        properties.setdefault(
            "kommunnamn",
            properties.get("name")
            or properties.get("KnNamn")
            or municipality_code,
        )

        selected_features.append(feature)

    result = {
        "type": "FeatureCollection",
        "features": selected_features,
    }

    output_path = Path("vg_municipalities.geojson")

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"Skrev {len(selected_features)} kommuner "
        f"till {output_path}"
    )

    if len(selected_features) != 49:
        raise RuntimeError(
            "Förväntade 49 kommuner men fick "
            f"{len(selected_features)}."
        )


if __name__ == "__main__":
    main()
