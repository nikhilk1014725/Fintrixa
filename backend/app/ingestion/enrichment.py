"""Cross-ticker enrichment of ingestion output.

Pragmatic stand-in for a real sector-PE data source (per the approved
fix): computes sector_pe as the peer-group mean trailing_pe across the
stocks we've already fetched from yfinance, instead of leaving it
permanently null. This is only meaningful if the fetched universe has
at least two stocks per sector with a usable trailing_pe — see
`enrich_sector_pe` for the exact skip conditions.
"""


def enrich_sector_pe(fundamentals_by_ticker: dict[str, dict]) -> dict[str, dict]:
    """Fill in `sector_pe` on each stock's fundamentals dict as the mean
    `trailing_pe` of its sector peers within the given batch.

    Grouping/averaging rules:
    - Stocks with `sector` None are skipped from grouping entirely (their
      own sector_pe stays None too — no peer group to compare against).
    - Within a sector group, stocks with `trailing_pe` None are skipped
      from the average (but can still receive a sector_pe if enough
      peers have usable trailing_pe).
    - A sector needs at least 2 members with usable trailing_pe for the
      mean to count as a real peer comparison. If fewer than 2, every
      stock in that sector keeps `sector_pe` as None — no guessing.

    Returns a new dict (does not mutate the input) with the same shape,
    `sector_pe` overwritten where a valid peer-group mean was computed.
    """
    sector_pes: dict[str, list[float]] = {}
    for data in fundamentals_by_ticker.values():
        sector = data.get("sector")
        pe = data.get("trailing_pe")
        if sector is None or pe is None:
            continue
        sector_pes.setdefault(sector, []).append(pe)

    sector_means = {
        sector: sum(pes) / len(pes)
        for sector, pes in sector_pes.items()
        if len(pes) >= 2
    }

    enriched = {}
    for ticker, data in fundamentals_by_ticker.items():
        row = dict(data)
        sector = row.get("sector")
        row["sector_pe"] = sector_means.get(sector) if sector is not None else None
        enriched[ticker] = row
    return enriched
