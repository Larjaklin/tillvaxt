"""Monthly, configuration-driven regional statistics pipeline for Tillväxt VG.

Reads active rows from indicator_config, fetches SCB/Kolada/AF data, normalizes rows to
regional_statistics and upserts on (municipality_code, indicator_name, year, industry, sex).
"""
from __future__ import annotations

import itertools
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx
from supabase import create_client

LOG = logging.getLogger("tillvaxt.pipeline")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)

SCB_API = "https://api.scb.se/OV0104/v1/doris/sv/ssd/START"
KOLADA_API = "https://api.kolada.se/v2"
PAGE_SIZE = 1000

VG_MUNICIPALITIES = {
    "1401": "Härryda",
    "1402": "Partille",
    "1407": "Öckerö",
    "1415": "Stenungsund",
    "1419": "Tjörn",
    "1421": "Orust",
    "1427": "Sotenäs",
    "1430": "Munkedal",
    "1435": "Tanum",
    "1438": "Dals-Ed",
    "1439": "Färgelanda",
    "1440": "Ale",
    "1441": "Lerum",
    "1442": "Vårgårda",
    "1443": "Bollebygd",
    "1444": "Grästorp",
    "1445": "Essunga",
    "1446": "Karlsborg",
    "1447": "Gullspång",
    "1452": "Tranemo",
    "1460": "Bengtsfors",
    "1461": "Mellerud",
    "1462": "Lilla Edet",
    "1463": "Mark",
    "1465": "Svenljunga",
    "1466": "Herrljunga",
    "1470": "Vara",
    "1471": "Götene",
    "1472": "Tibro",
    "1473": "Töreboda",
    "1480": "Göteborg",
    "1481": "Mölndal",
    "1482": "Kungälv",
    "1484": "Lysekil",
    "1485": "Uddevalla",
    "1486": "Strömstad",
    "1487": "Vänersborg",
    "1488": "Trollhättan",
    "1489": "Alingsås",
    "1490": "Borås",
    "1491": "Ulricehamn",
    "1492": "Åmål",
    "1493": "Mariestad",
    "1494": "Lidköping",
    "1495": "Skara",
    "1496": "Skövde",
    "1497": "Hjo",
    "1498": "Tidaholm",
    "1499": "Falköping",
}


@dataclass(frozen=True)
class Indicator:
    short_name: str
    description: str
    source: str
    unit: str
    source_identifier: str
    source_filter: dict[str, Any] | None


def ordered_category_codes(dimension: dict[str, Any]) -> list[str]:
    category = dimension.get("category", {})
    index = category.get("index", {})

    if isinstance(index, list):
        labels = category.get("label", {})
        return sorted(
            labels,
            key=lambda code: index.index(code) if code in index else 10**9,
        )

    return sorted(index.keys(), key=lambda code: index[code])


def parse_jsonstat2(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand JSON-stat2's flat value array into dimension rows."""
    dimension_ids = payload.get("id") or []
    dimensions = payload.get("dimension") or {}
    values = payload.get("value") or []

    if not dimension_ids or not dimensions:
        return []

    codes_by_dimension = [
        ordered_category_codes(dimensions[dimension_id])
        for dimension_id in dimension_ids
    ]

    labels_by_dimension = {
        dimension_id: (
            dimensions.get(dimension_id, {})
            .get("category", {})
            .get("label", {})
            or {}
        )
        for dimension_id in dimension_ids
    }

    rows: list[dict[str, Any]] = []

    for offset, combination in enumerate(
        itertools.product(*codes_by_dimension)
    ):
        if offset >= len(values):
            break

        row = {
            dimension_id: {
                "code": code,
                "label": labels_by_dimension[dimension_id].get(code, code),
            }
            for dimension_id, code in zip(
                dimension_ids,
                combination,
            )
        }
        row["value"] = values[offset]
        rows.append(row)

    return rows


def normalize_scb(
    rows: Iterable[dict[str, Any]],
    indicator: Indicator,
) -> list[dict[str, Any]]:
    normalized_rows = []

    for row in rows:
        region = row.get("Region") or row.get("region")
        year = row.get("Tid") or row.get("time") or row.get("År")

        if not region or not year or row.get("value") is None:
            continue

        municipality_code = str(region["code"])

        if municipality_code not in VG_MUNICIPALITIES:
            continue

        industry = (
            row.get("Naringsgren")
            or row.get("SNI")
            or {"label": "alla"}
        ).get("label", "alla")

        sex = (
            row.get("Kon")
            or row.get("Kön")
            or {"label": "totalt"}
        ).get("label", "totalt")

        normalized_rows.append(
            {
                "municipality_code": municipality_code,
                "municipality_name": VG_MUNICIPALITIES.get(
                    municipality_code,
                    region.get("label", municipality_code),
                ),
                "year": int(str(year["code"])[:4]),
                "source": "SCB",
                "indicator_name": indicator.short_name,
                "industry": industry,
                "sex": sex,
                "value": float(row["value"]),
                "unit": indicator.unit,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return normalized_rows


async def fetch_scb(
    client: httpx.AsyncClient,
    indicator: Indicator,
) -> list[dict[str, Any]]:
    if not indicator.source_filter:
        raise ValueError("SCB-indikator saknar source_filter")

    url = f"{SCB_API}/{indicator.source_identifier.strip('/')}"

    response = await client.post(
    url,
    json=indicator.source_filter,
    timeout=120,
)

if response.is_error:
    raise RuntimeError(
        f"SCB svarade {response.status_code} för {url}: "
        f"{response.text}"
    )

return normalize_scb(
    parse_jsonstat2(response.json()),
    indicator,
)


async def fetch_kolada(
    client: httpx.AsyncClient,
    indicator: Indicator,
) -> list[dict[str, Any]]:
    normalized_rows = []

    for municipality_code, municipality_name in VG_MUNICIPALITIES.items():
        url = (
            f"{KOLADA_API}/data/kpi/"
            f"{indicator.source_identifier}/municipality/{municipality_code}"
        )

        response = await client.get(url, timeout=30)
        response.raise_for_status()

        for item in response.json().get("values", []):
            period = str(item.get("period", ""))[:4]
            value = item.get("value")

            if not period.isdigit() or value is None:
                continue

            normalized_rows.append(
                {
                    "municipality_code": municipality_code,
                    "municipality_name": municipality_name,
                    "year": int(period),
                    "source": "Kolada",
                    "indicator_name": indicator.short_name,
                    "industry": "alla",
                    "sex": "totalt",
                    "value": float(value),
                    "unit": indicator.unit,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    return normalized_rows


async def fetch_indicator(
    client: httpx.AsyncClient,
    indicator: Indicator,
) -> list[dict[str, Any]]:
    source = indicator.source.lower()

    if source == "scb":
        return await fetch_scb(client, indicator)

    if source == "kolada":
        return await fetch_kolada(client, indicator)

    if source in {
        "arbetsformedlingen",
        "arbetsförmedlingen",
        "af",
    }:
        raise NotImplementedError(
            "Arbetsförmedlingen saknar öppet kommun-API; "
            "indikatorn hoppas över."
        )

    raise ValueError(f"Okänd datakälla: {indicator.source}")


def chunks(
    items: list[dict[str, Any]],
    size: int = PAGE_SIZE,
):
    for index in range(0, len(items), size):
        yield items[index:index + size]


async def main() -> None:
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    config_rows = (
        supabase.table("indicator_config")
        .select("*")
        .eq("active", True)
        .execute()
        .data
        or []
    )

    indicators = [
        Indicator(
            row["short_name"],
            row.get("description", ""),
            row["source"],
            row.get("unit", ""),
            row["source_identifier"],
            row.get("source_filter"),
        )
        for row in config_rows
    ]

    LOG.info(
        "Startar pipeline för %s aktiva indikatorer",
        len(indicators),
    )

    async with httpx.AsyncClient() as client:
        for indicator in indicators:
            try:
                normalized_rows = await fetch_indicator(
                    client,
                    indicator,
                )

                for batch in chunks(normalized_rows):
                    (
                        supabase.table("regional_statistics")
                        .upsert(
                            batch,
                            on_conflict=(
                                "municipality_code,"
                                "indicator_name,"
                                "year,"
                                "industry,"
                                "sex"
                            ),
                        )
                        .execute()
                    )

                LOG.info(
                    "%s: sparade %s rader",
                    indicator.short_name,
                    len(normalized_rows),
                )
            except Exception as error:
                LOG.exception(
                    "%s misslyckades och hoppas över: %s",
                    indicator.short_name,
                    error,
                )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
