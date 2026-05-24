"""Lazy Google Sheets reader via Polars IO plugin API."""

from __future__ import annotations

from collections.abc import Iterator
from io import StringIO

import polars as pl
from polars.io.plugins import register_io_source

from . import exceptions
from .fetch import fetch_raw
from .url import build_gviz_url, from_url


def scan_google_sheet(
    sheet_name: str,
    sheet_id: str | None = None,
    url: str | None = None,
    *,
    timeout: int = 10,
    parse_dates: bool = True,
    batch_size: int = 1_000,
) -> pl.LazyFrame:
    """Scan a public Google Sheet as a Polars LazyFrame via the IO plugin API.

    Registered as a lazy source so it participates in Polars query
    optimisation — projection pushdown, predicate pushdown, early stopping,
    and streaming in batches are all supported.

    Parameters
    ----------
    sheet_name:
        The tab name to read (as shown on the sheet tab in Google Sheets).
    sheet_id:
        The spreadsheet ID from the URL. Mutually exclusive with ``url``.
    url:
        A full Google Sheets URL. The sheet ID is extracted automatically.
        Mutually exclusive with ``sheet_id``.
    timeout:
        HTTP request timeout in seconds.
    parse_dates:
        Attempt automatic date/datetime parsing.
    batch_size:
        Number of rows per batch yielded to the Polars engine.

    Returns
    -------
    pl.LazyFrame

    Raises
    ------
    ConfigurationError
        If neither or both of ``sheet_id`` / ``url`` are provided.
    SheetFetchError
        If the HTTP request fails or returns a non-200 status.
    NetworkError
        On connection or transport failure.

    Notes
    -----
    Google Sheets CSV export does not support partial reads — the full sheet
    is always downloaded in a single HTTP request. Projection and predicate
    pushdown are applied in Python after the download, so they reduce
    processing cost but not network cost.

    Examples
    --------
    >>> lf = scan_google_sheet("Sheet1", sheet_id="1BxiMVs0XRA5nFMdKvBdBZjgm...")
    >>> lf.filter(pl.col("year") == 2025).select("vessel", "amount").collect()

    >>> lf = scan_google_sheet(
    ...     "Sheet1",
    ...     url="https://docs.google.com/spreadsheets/d/1BxiMVs0.../edit",
    ... )
    """

    _outer_batch_size = batch_size
    match (sheet_id, url):
        case (None, None):
            raise exceptions.ConfigurationError("Provide either sheet_id or url, not neither.")
        case (_, None):
            assert sheet_id is not None
            resolved_url = build_gviz_url(sheet_id, sheet_name)
        case (None, _):
            assert url is not None
            resolved_url = from_url(url, sheet_name)
        case _:
            raise exceptions.ConfigurationError("Provide either sheet_id or url, not both.")

    # One upfront fetch to resolve the schema — unavoidable for CSV over HTTP.
    raw_csv = fetch_raw(resolved_url, timeout=timeout, sheet_name=sheet_name)

    schema = pl.read_csv(
        StringIO(raw_csv),
        try_parse_dates=parse_dates,
        infer_schema_length=10_000,
        n_rows=0,  # schema only, no data rows needed
    ).schema

    def source_generator(
        with_columns: list[str] | None,
        predicate: pl.Expr | None,
        n_rows: int | None,
        batch_size: int | None,
    ) -> Iterator[pl.DataFrame]:
        """Produce batches of rows, honouring pushdown hints from the engine."""
        _batch = batch_size or _outer_batch_size

        lf = pl.read_csv(
            StringIO(raw_csv),
            try_parse_dates=parse_dates,
            infer_schema_length=10_000,
        ).lazy()

        # Apply pushdowns — filtering in Python, not at source (HTTP limitation)
        if with_columns is not None:
            lf = lf.select(with_columns)
        if predicate is not None:
            lf = lf.filter(predicate)
        if n_rows is not None:
            lf = lf.head(n_rows)

        df = lf.collect()
        assert isinstance(df, pl.DataFrame)

        for offset in range(0, df.height, _batch):
            yield df.slice(offset, _batch)

    return register_io_source(io_source=source_generator, schema=schema)


def read_google_sheet(
    sheet_name: str,
    sheet_id: str | None = None,
    url: str | None = None,
    *,
    timeout: int = 10,
    parse_dates: bool = True,
) -> pl.DataFrame:
    """Read a public Google Sheet into a Polars DataFrame.

    Convenience wrapper around ``scan_google_sheet`` that collects immediately.
    Prefer ``scan_google_sheet`` when chaining filters or projections before
    collecting, to avoid loading unused columns into memory.

    Parameters
    ----------
    sheet_name:
        The tab name to read.
    sheet_id:
        The spreadsheet ID. Mutually exclusive with ``url``.
    url:
        A full Google Sheets URL. Mutually exclusive with ``sheet_id``.
    timeout:
        HTTP request timeout in seconds.
    parse_dates:
        Attempt automatic date/datetime parsing.

    Returns
    -------
    pl.DataFrame

    Examples
    --------
    >>> df = read_google_sheet("Sheet1", sheet_id="1BxiMVs0XRA5nFMdKvBdBZjgm...")
    >>> df = read_google_sheet(
    ...     "Sheet1",
    ...     url="https://docs.google.com/spreadsheets/d/1BxiMVs0.../edit",
    ... )
    """
    df = scan_google_sheet(
        sheet_name,
        sheet_id=sheet_id,
        url=url,
        timeout=timeout,
        parse_dates=parse_dates,
    ).collect()
    assert isinstance(df, pl.DataFrame)
    return df
