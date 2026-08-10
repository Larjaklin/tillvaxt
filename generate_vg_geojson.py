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
    import importlib
    import pkgutil

    import swemaps

    print("Swemaps finns i:", swemaps.__file__)

    public_names = [
        name
        for name in dir(swemaps)
        if not name.startswith("_")
    ]

    print("Publika namn i swemaps:", public_names)

    if hasattr(swemaps, "__path__"):
        submodules = [
            module.name
            for module in pkgutil.iter_modules(
                swemaps.__path__
            )
        ]
    else:
        submodules = []

    print("Undermoduler i swemaps:", submodules)

    for submodule_name in submodules:
        full_name = f"swemaps.{submodule_name}"

        try:
            module = importlib.import_module(full_name)

            names = [
                name
                for name in dir(module)
                if not name.startswith("_")
            ]

            print(
                f"Publika namn i {full_name}:",
                names,
            )
        except Exception as error:
            print(
                f"Kunde inte läsa {full_name}:",
                repr(error),
            )

    raise RuntimeError(
        "Diagnostik klar. Se GitHub Actions-loggen "
        "för swemaps API."
    )
    
if __name__ == "__main__":
    main()
