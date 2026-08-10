"""Skapa Leaflet-kompatibel GeoJSON för Västra Götalands kommuner.

Swemaps inbyggda kommunkarta används direkt. Ingen manuell
koordinatomvandling ska göras.
"""

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import swemaps
from shapely import from_wkb
from shapely.geometry import mapping


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
    map_path = swemaps.get_path("kommun")

    print(f"Läser kommunkarta från {map_path}")

    municipality_table = pq.read_table(
        map_path
    )

    required_columns = {
        "kommun_kod",
        "kommun",
        "geometry",
    }

    missing_columns = required_columns.difference(
        municipality_table.column_names
    )

    if missing_columns:
        raise RuntimeError(
            "Kommunkartan saknar förväntade kolumner: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    selected_codes = pa.array(
        sorted(VG_CODES),
        type=pa.string(),
    )

    selected_rows = pc.is_in(
        municipality_table["kommun_kod"],
        value_set=selected_codes,
    )

    vg_table = municipality_table.filter(
        selected_rows
    )

    print(
        f"Valde {vg_table.num_rows} kommuner "
        "från kommunkartan"
    )

    if vg_table.num_rows != 49:
        found_codes = {
            str(value)
            for value in (
                vg_table["kommun_kod"]
                .to_pylist()
            )
        }

        missing_codes = sorted(
            VG_CODES.difference(found_codes)
        )

        raise RuntimeError(
            "Förväntade 49 kommuner men fick "
            f"{vg_table.num_rows}. "
            "Saknade koder: "
            + ", ".join(missing_codes)
        )

    municipality_codes = (
        vg_table["kommun_kod"].to_pylist()
    )

    municipality_names = (
        vg_table["kommun"].to_pylist()
    )

    geometry_values = (
        vg_table["geometry"].to_pylist()
    )

    features = []

    for (
        municipality_code,
        municipality_name,
        geometry_value,
    ) in zip(
        municipality_codes,
        municipality_names,
        geometry_values,
        strict=True,
    ):
        if geometry_value is None:
            raise RuntimeError(
                "Kommunen "
                f"{municipality_code} "
                "saknar geometri."
            )

        geometry = from_wkb(
            bytes(geometry_value)
        )

        code = str(
            municipality_code
        )[-4:]

        name = str(
            municipality_name
        )

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "kommun_kod": code,
                    "kommun": name,
                    "kommunkod": code,
                    "kommunnamn": name,
                },
                "geometry": mapping(
                    geometry
                ),
            }
        )

    if len(features) != 49:
        raise RuntimeError(
            "GeoJSON-konverteringen gav "
            f"{len(features)} objekt "
            "i stället för 49."
        )

    output = {
        "type": "FeatureCollection",
        "features": features,
    }

    output_path = Path(
        "vg_municipalities.geojson"
    )

    output_path.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    print(
        f"Skrev {len(features)} kommuner "
        f"till {output_path}"
    )


if __name__ == "__main__":
    main()
