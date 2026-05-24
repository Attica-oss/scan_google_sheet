"""Utilities for parsing Google Sheets URLs."""

import re
from urllib.parse import parse_qs, quote, urlparse

from .exceptions import SheetURLError


def extract_sheet_id(url: str) -> str:
    """Extract the spreadsheet ID from a Google Sheets URL or return as-is if already an ID."""
    pattern = r"/spreadsheets/d/([a-zA-Z0-9_-]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    # Assume it's already a bare sheet ID
    if re.fullmatch(r"[a-zA-Z0-9_-]+", url):
        return url
    raise SheetURLError(f"Could not extract sheet ID from: {url!r}", raw=url)


def extract_gid(url: str) -> str | None:
    """Extract the gid (tab/sheet index) from a Google Sheets URL, if present."""
    parsed = urlparse(url)
    # gid can appear in the fragment: #gid=123456
    fragment_params = parse_qs(parsed.fragment)
    if "gid" in fragment_params:
        return fragment_params["gid"][0]
    # or in the query string
    query_params = parse_qs(parsed.query)
    if "gid" in query_params:
        return query_params["gid"][0]
    return None


def build_export_url(sheet_id: str, gid: str | None = None) -> str:
    """Build the CSV export URL for a public Google Sheet (by gid/tab index)."""
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid is not None:
        base += f"&gid={gid}"
    return base


def build_gviz_url(sheet_id: str, sheet_name: str) -> str:
    """Build the gviz CSV export URL for a public Google Sheet (by sheet name).

    Preferred over the ``/export`` URL when the sheet name is known, as it
    allows selecting a specific tab by name rather than numeric gid.

    Examples:
        >>> build_gviz_url("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms", "Sheet1")
        'https://docs.google.com/spreadsheets/d/1BxiMVs0.../gviz/tq?tqx=out:csv&sheet=Sheet1'
    """
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"


def from_url(url: str, sheet_name: str) -> str:
    """Extract the sheet ID from a full Google Sheets URL and build a gviz export URL.

    Parameters
    ----------
    url:
        Any Google Sheets URL containing a spreadsheet ID.
    sheet_name:
        The tab name to export.

    Returns
    -------
    str
        A ready-to-fetch gviz CSV export URL.

    Raises
    ------
    SheetURLError
        If no sheet ID can be extracted from ``url``.
    """
    sheet_id = extract_sheet_id(url)
    return build_gviz_url(sheet_id, sheet_name)
