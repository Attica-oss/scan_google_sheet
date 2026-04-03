"""Fetch CSV data from a public Google Sheets export URL using httpx."""

import httpx

from . import exceptions


def fetch_raw(url: str, *, timeout: int = 30, sheet_name: str = "") -> str:
    """Fetch raw CSV text from a Google Sheets gviz export URL.

    Parameters
    ----------
    url:
        The full gviz CSV export URL (use ``build_gviz_url`` or ``from_url``).
    timeout:
        Request timeout in seconds.
    sheet_name:
        Used in error messages to identify which sheet failed.

    Returns
    -------
    str
        Raw CSV text.

    Raises
    ------
    SheetFetchError
        On non-200 HTTP status or timeout.
    NetworkError
        On connection/transport failure (no response received).
    """
    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "read-sheet/0.1.0"},
        )
    except httpx.TimeoutException as e:
        raise exceptions.SheetFetchError(
            f"Request timed out after {timeout} seconds", url=url, cause=e
        ) from e
    except httpx.RequestError as e:
        raise exceptions.NetworkError(f"Network error: {e}", url=url, cause=e) from e

    if response.status_code != 200:
        label = f"'{sheet_name}'" if sheet_name else url
        raise exceptions.SheetFetchError(
            f"Failed to fetch {label}. "
            f"Status: {response.status_code}, Reason: {response.reason_phrase}",
            url=url,
            status_code=response.status_code,
        )

    return response.text


# # Backwards-compatible alias used by read_sheet()
# def fetch_csv(export_url: str, timeout: int = 30) -> str:
#     return fetch_raw(export_url, timeout=timeout)
