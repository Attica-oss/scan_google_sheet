"""Parse raw CSV text into a Polars DataFrame."""

import io

import polars as pl

from .exceptions import _POLARS_PARSE_ERRORS, SheetParseError


def parse_csv(
    csv_text: str,
    *,
    infer_schema_length: int | None = 100,
    null_values: list[str] | None = None,
    try_parse_dates: bool = False,
    schema_overrides: dict[str, pl.DataType] | None = None,
) -> pl.DataFrame:
    """Parse CSV text into a Polars DataFrame.

    Parameters
    ----------
    csv_text:
        Raw CSV string fetched from Google Sheets export.
    infer_schema_length:
        Number of rows used to infer column types. Pass `None` to read all rows.
    null_values:
        Additional strings to treat as null (e.g. ``["N/A", "-"]``).
    try_parse_dates:
        Attempt to parse date-like strings automatically.
    schema_overrides:
        Map of column name → Polars dtype to override inferred types.

    Returns
    -------
    pl.DataFrame
    """
    _null_values = ["", "NULL", "null", "None", "NA"] + (null_values or [])

    try:
        return pl.read_csv(
            io.StringIO(csv_text),
            infer_schema_length=infer_schema_length,
            null_values=_null_values,
            try_parse_dates=try_parse_dates,
            schema_overrides=schema_overrides,
        )
    except tuple(_POLARS_PARSE_ERRORS) as e:
        raise SheetParseError.from_polars(e, step="parse_csv") from e
    except Exception as e:
        raise SheetParseError(f"Unexpected error parsing CSV: {e}", cause=e) from e
