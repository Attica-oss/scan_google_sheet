"""read_sheet — Read public Google Sheets into Polars DataFrames."""

import polars as pl

from .exceptions import (
    ConfigurationError,
    NetworkError,
    ReadSheetError,
    SheetFetchError,
    SheetParseError,
    SheetURLError,
)
from .fetch import fetch_raw
from .parse import parse_csv
from .scan import read_google_sheet, scan_google_sheet
from .url import build_export_url, build_gviz_url, extract_gid, extract_sheet_id, from_url

__all__ = [
    # main API
    "read_google_sheet",
    "scan_google_sheet",
    # exceptions
    "ReadSheetError",
    "SheetURLError",
    "SheetFetchError",
    "SheetParseError",
    "NetworkError",
    "ConfigurationError",
    # url utilities
    "extract_sheet_id",
    "extract_gid",
    "build_export_url",
    "build_gviz_url",
    "from_url",
]


def read_sheet(
    url_or_id: str,
    *,
    gid: str | None = None,
    timeout: int = 30,
    infer_schema_length: int | None = 100,
    null_values: list[str] | None = None,
    try_parse_dates: bool = False,
    schema_overrides: dict[str, pl.DataType] | None = None,
) -> pl.DataFrame:
    """Read a public Google Sheet into a Polars DataFrame.

    Parameters
    ----------
    url_or_id:
        Either a full Google Sheets URL or a bare spreadsheet ID.
        If a URL is provided, the ``gid`` is extracted automatically
        unless overridden by the ``gid`` parameter.
    gid:
        Tab/sheet index (gid). Overrides any gid found in ``url_or_id``.
        Defaults to the first sheet if omitted.
    timeout:
        HTTP request timeout in seconds.
    infer_schema_length:
        Rows used to infer column types. ``None`` = all rows.
    null_values:
        Extra strings to treat as null (on top of the built-in defaults).
    try_parse_dates:
        Attempt automatic date parsing.
    schema_overrides:
        Override inferred dtypes per column.

    Returns
    -------
    pl.DataFrame

    Examples
    --------
    >>> df = read_sheet("https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=0")
    >>> df = read_sheet("SHEET_ID", gid="123456789")
    """
    sheet_id = extract_sheet_id(url_or_id)

    # gid: explicit param wins, then try extracting from URL, then None (first sheet)
    resolved_gid = gid if gid is not None else extract_gid(url_or_id)

    export_url = build_export_url(sheet_id, resolved_gid)
    csv_text = fetch_raw(export_url, timeout=timeout)

    return parse_csv(
        csv_text,
        infer_schema_length=infer_schema_length,
        null_values=null_values,
        try_parse_dates=try_parse_dates,
        schema_overrides=schema_overrides,
    )
