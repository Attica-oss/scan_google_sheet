"""Tests for URL parsing and construction utilities."""

import pytest

from scan_google_sheet.exceptions import ReadSheetError, SheetURLError
from scan_google_sheet.url import (
    build_export_url,
    build_gviz_url,
    extract_gid,
    extract_sheet_id,
    from_url,
)

SHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"


class TestExtractSheetId:
    def test_full_edit_url(self) -> None:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"
        assert extract_sheet_id(url) == SHEET_ID

    def test_bare_id(self) -> None:
        assert extract_sheet_id(SHEET_ID) == SHEET_ID

    def test_pub_url(self) -> None:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/pub"
        assert extract_sheet_id(url) == SHEET_ID

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(SheetURLError) as exc_info:
            extract_sheet_id("not a valid url !!!")
        assert exc_info.value.raw == "not a valid url !!!"

    def test_error_is_base_exception(self) -> None:
        # from read_sheet.exceptions import ReadSheetError

        with pytest.raises(ReadSheetError):
            extract_sheet_id("not a valid url !!!")


class TestExtractGid:
    def test_gid_in_fragment(self) -> None:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=123456"
        assert extract_gid(url) == "123456"

    def test_gid_in_query(self) -> None:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=789"
        assert extract_gid(url) == "789"

    def test_no_gid_returns_none(self) -> None:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
        assert extract_gid(url) is None

    def test_gid_zero(self) -> None:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"
        assert extract_gid(url) == "0"


class TestBuildExportUrl:
    def test_without_gid(self) -> None:
        url = build_export_url(SHEET_ID)
        assert url == f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    def test_with_gid(self) -> None:
        url = build_export_url(SHEET_ID, gid="42")
        assert url.endswith("&gid=42")


class TestBuildGvizUrl:
    def test_structure(self) -> None:
        url = build_gviz_url(SHEET_ID, "Sheet1")
        assert f"/d/{SHEET_ID}/gviz/tq" in url
        assert "tqx=out:csv" in url
        assert "sheet=Sheet1" in url

    def test_sheet_name_with_spaces(self) -> None:
        url = build_gviz_url(SHEET_ID, "My Sheet")
        assert "sheet=My Sheet" in url


class TestFromUrl:
    def test_extracts_and_builds(self) -> None:
        full_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"
        result = from_url(full_url, "Sheet1")
        assert SHEET_ID in result
        assert "sheet=Sheet1" in result

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(SheetURLError):
            from_url("not-a-url!!!", "Sheet1")
