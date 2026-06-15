# Scan Google Sheet

Read public Google Sheets into Polars DataFrames and LazyFrames — no auth, no service accounts, no API keys.

[![PyPI](https://img.shields.io/pypi/v/scan-google-sheet)](https://pypi.org/project/scan-google-sheet/)
[![Python](https://img.shields.io/pypi/pyversions/scan-google-sheet)](https://pypi.org/project/scan-google-sheet/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/Attica-oss/scan_google_sheet/actions/workflows/ci.yml/badge.svg)](https://github.com/Attica-oss/scan_google_sheet/actions/workflows/ci.yml)

---

## Requirements

- Python ≥ 3.13
- The spreadsheet must be set to **Anyone with the link can view**

---

## Installation

```bash
pip install scan-google-sheet
# or
uv add scan-google-sheet
```

---

## Quick start

```python
from scan_google_sheet import read_google_sheet, scan_google_sheet
```

**Eager — returns a `DataFrame` immediately:**

```python
df = read_google_sheet("Sheet1", sheet_id="1BxiMVs0XRA5nFMdKvBdBZjgm...")
```

**Lazy — returns a `LazyFrame`, participates in Polars query optimisation:**

```python
lf = scan_google_sheet("Sheet1", sheet_id="1BxiMVs0XRA5nFMdKvBdBZjgm...")

df = (
    lf
    .filter(pl.col("year") == 2025)
    .select("vessel", "amount")
    .collect()
)
```

You can also pass a full Google Sheets URL instead of a bare sheet ID:

```python
df = read_google_sheet(
    "Sheet1",
    url="https://docs.google.com/spreadsheets/d/1BxiMVs0.../edit#gid=0",
)
```

---

## API

### `read_google_sheet`

```python
def read_google_sheet(
    sheet_name: str,
    sheet_id: str | None = None,
    url: str | None = None,
    *,
    timeout: int = 10,
    parse_dates: bool = True,
) -> pl.DataFrame
```

Fetches the sheet and returns a collected `DataFrame`. Use this when you want the data immediately and do not need lazy evaluation.

### `scan_google_sheet`

```python
def scan_google_sheet(
    sheet_name: str,
    sheet_id: str | None = None,
    url: str | None = None,
    *,
    timeout: int = 10,
    parse_dates: bool = True,
    batch_size: int = 1_000,
) -> pl.LazyFrame
```

Returns a `LazyFrame` registered via the Polars IO plugin API. Projection pushdown, predicate pushdown, `head()`, and streaming are all supported.

> **Note:** Google Sheets does not support partial HTTP reads. The full sheet is always downloaded in one request. Pushdowns reduce processing cost, not network cost.

**Parameters shared by both functions:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sheet_name` | `str` | — | Tab name as shown in Google Sheets |
| `sheet_id` | `str \| None` | `None` | Spreadsheet ID from the URL |
| `url` | `str \| None` | `None` | Full Google Sheets URL (ID extracted automatically) |
| `timeout` | `int` | `10` | HTTP timeout in seconds |
| `parse_dates` | `bool` | `True` | Attempt automatic date/datetime parsing |

Provide either `sheet_id` or `url`, not both.

---

## URL utilities

```python
from scan_google_sheet import extract_sheet_id, build_gviz_url, from_url

# Extract the sheet ID from any Google Sheets URL
sheet_id = extract_sheet_id("https://docs.google.com/spreadsheets/d/ABC123/edit")
# "ABC123"

# Build a gviz CSV export URL from a sheet ID and tab name
url = build_gviz_url("ABC123", "Sheet1")
# "https://docs.google.com/spreadsheets/d/ABC123/gviz/tq?tqx=out:csv&sheet=Sheet1"

# Build a gviz URL directly from a full Google Sheets URL
url = from_url("https://docs.google.com/spreadsheets/d/ABC123/edit", "Sheet1")
```

---

## Error handling

All exceptions inherit from `ReadSheetError`, so you can catch everything with one handler or branch on specific types:

```python
from scan_google_sheet import (
    read_google_sheet,
    ReadSheetError,
    SheetFetchError,
    SheetURLError,
    SheetParseError,
    NetworkError,
    ConfigurationError,
)

try:
    df = read_google_sheet("Sheet1", sheet_id="...")
except ReadSheetError as e:
    match e:
        case SheetFetchError() if e.is_auth_error:
            print("Make the sheet public (Share → Anyone with the link)")
        case SheetFetchError() if e.is_not_found:
            print(f"Sheet not found — check the ID: {e.url}")
        case NetworkError():
            print(f"No connection: {e.cause}")
        case SheetURLError(raw=r):
            print(f"Could not parse URL: {r!r}")
        case SheetParseError():
            print(f"CSV parse failed: {e.cause}")
        case ConfigurationError():
            print(str(e))
```

### Exception hierarchy

```
ReadSheetError
├── SheetURLError       malformed URL or unextractable sheet ID  (.raw)
├── SheetFetchError     non-200 HTTP response                    (.url, .status_code)
│                                                                (.is_auth_error, .is_not_found)
├── SheetParseError     CSV or Polars parsing failure            (.column)
├── NetworkError        transport failure, no response received  (.url)
└── ConfigurationError  invalid argument combination
```

---

## Making your sheet public

In Google Sheets: **Share → Change to Anyone with the link → Viewer → Done.**

The export URL used by this library (`gviz/tq?tqx=out:csv`) requires the sheet to be publicly readable. No data is ever written.

---

## How it works

```
Google Sheets URL / ID
        │
        ▼
  build_gviz_url()          constructs the CSV export URL
        │
        ▼
    fetch_raw()             httpx GET with follow_redirects=True
        │
        ▼
  pl.scan_csv()             parsed into a Polars LazyFrame
        │
        ▼
register_io_source()        registered as a Polars IO plugin
        │
        ▼
  LazyFrame / DataFrame     ready for your pipeline
```

---

## Development

```bash
git clone https://github.com/Attica-oss/scan_google_sheet
cd scan_google_sheet
uv sync --group dev
uv run pytest
```

Lint and format:

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run ty check src/
```

---

## Changelog

### 0.1.0 (2025)
- Initial release
- `read_google_sheet` and `scan_google_sheet`
- Polars IO plugin for lazy evaluation
- Structured exception hierarchy
- Full test suite with `pytest-httpx`

---

## License

[MIT](LICENSE) © 2025 Attica-oss
