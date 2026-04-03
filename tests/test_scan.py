"""Tests for scan_google_sheet and read_google_sheet."""

import polars as pl
import pytest
from pytest_httpx import HTTPXMock

from scan_google_sheet.exceptions import ConfigurationError, SheetFetchError
from scan_google_sheet.scan import read_google_sheet, scan_google_sheet

SHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
SHEET_NAME = "Sheet1"
GVIZ_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
)
SAMPLE_CSV = """\
vessel,year,amount
MSC ANNA,2024,1500.50
EVER GIVEN,2024,3200.00
MSC ANNA,2025,1750.75
"""


class TestConfigurationError:
    def test_neither_raises(self) -> None:
        with pytest.raises(ConfigurationError, match="neither"):
            scan_google_sheet(SHEET_NAME)

    def test_both_raises(self) -> None:
        with pytest.raises(ConfigurationError, match="both"):
            scan_google_sheet(
                SHEET_NAME,
                sheet_id=SHEET_ID,
                url="https://docs.google.com/spreadsheets/d/OTHER/edit",
            )


class TestScanGoogleSheet:
    def test_returns_lazy_frame(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        lf = scan_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        assert isinstance(lf, pl.LazyFrame)

    def test_schema_columns(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        lf = scan_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        assert set(lf.collect_schema().names()) == {"vessel", "year", "amount"}

    def test_collect_row_count(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        lf = scan_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        df = lf.collect()
        assert isinstance(df, pl.DataFrame)
        assert df.height == 3

    def test_projection_pushdown(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        lf = scan_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        df = lf.select("vessel", "year").collect()
        assert isinstance(df, pl.DataFrame)
        assert df.columns == ["vessel", "year"]

    def test_predicate_pushdown(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        lf = scan_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        df = lf.filter(pl.col("year") == 2025).collect()
        assert isinstance(df, pl.DataFrame)
        assert df.height == 1
        assert df["vessel"][0] == "MSC ANNA"

    def test_from_url(self, httpx_mock: HTTPXMock) -> None:
        full_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        lf = scan_google_sheet(SHEET_NAME, url=full_url)
        assert isinstance(lf, pl.LazyFrame)

    def test_fetch_error_propagates(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, status_code=403)
        with pytest.raises(SheetFetchError) as exc_info:
            scan_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        assert exc_info.value.is_auth_error


class TestReadGoogleSheet:
    def test_returns_dataframe(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        df = read_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        assert isinstance(df, pl.DataFrame)

    def test_row_count(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        df = read_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        assert df.height == 3

    def test_values(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        df = read_google_sheet(SHEET_NAME, sheet_id=SHEET_ID)
        assert df["vessel"].to_list() == ["MSC ANNA", "EVER GIVEN", "MSC ANNA"]
        assert df["amount"][0] == pytest.approx(1500.50)
