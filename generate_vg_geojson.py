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
    import inspect
    from typing import get_args

    import swemaps
    from swemaps import utils

    print("Swemaps finns i:", swemaps.__file__)

    functions = [
        ("swemaps.fetch_map", swemaps.fetch_map),
        ("swemaps.get_path", swemaps.get_path),
        (
            "swemaps.table_to_geojson",
            swemaps.table_to_geojson,
        ),
    ]

    for name, function in functions:
        print()
        print("=" * 70)
        print("Funktion:", name)
        print("Signatur:", inspect.signature(function))
        print("Dokumentation:", inspect.getdoc(function))

        try:
            print("Källkod:")
            print(inspect.getsource(function))
        except Exception as error:
            print(
                "Kunde inte läsa källkoden:",
                repr(error),
            )

    print()
    print("=" * 70)
    print(
        "BuiltinMap-värden:",
        get_args(utils.BuiltinMap),
    )
    print(
        "ExtraMap-värden:",
        get_args(utils.ExtraMap),
    )

    raise RuntimeError(
        "API-diagnostik klar. Kopiera resultatet "
        "från GitHub Actions."
    )


if __name__ == "__main__":
    main()
