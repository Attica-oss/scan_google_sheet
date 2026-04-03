"""Tests for fetch_raw — HTTP layer mocked with pytest-httpx."""

import pytest
from pytest_httpx import HTTPXMock

from scan_google_sheet.exceptions import NetworkError, SheetFetchError
from scan_google_sheet.fetch import fetch_raw

GVIZ_URL = "https://docs.google.com/spreadsheets/d/SHEETID/gviz/tq?tqx=out:csv&sheet=Sheet1"
SAMPLE_CSV = "vessel,amount\nMSC ANNA,1500\n"


class TestFetchRawSuccess:
    def test_returns_csv_text(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        result = fetch_raw(GVIZ_URL, sheet_name="Sheet1")
        assert result == SAMPLE_CSV

    def test_user_agent_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, text=SAMPLE_CSV)
        fetch_raw(GVIZ_URL)
        request = httpx_mock.get_requests()[0]
        assert "read-sheet" in request.headers["user-agent"]


class TestFetchRawErrors:
    def test_401_raises_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, status_code=401)
        with pytest.raises(SheetFetchError) as exc_info:
            fetch_raw(GVIZ_URL, sheet_name="Sheet1")
        assert exc_info.value.status_code == 401
        assert exc_info.value.is_auth_error

    def test_403_raises_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, status_code=403)
        with pytest.raises(SheetFetchError) as exc_info:
            fetch_raw(GVIZ_URL, sheet_name="Sheet1")
        assert exc_info.value.is_auth_error

    def test_404_raises_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, status_code=404)
        with pytest.raises(SheetFetchError) as exc_info:
            fetch_raw(GVIZ_URL, sheet_name="Sheet1")
        assert exc_info.value.is_not_found

    def test_500_raises_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, status_code=500)
        with pytest.raises(SheetFetchError):
            fetch_raw(GVIZ_URL, sheet_name="Sheet1")

    def test_timeout_raises_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        import httpx

        httpx_mock.add_exception(httpx.TimeoutException("timed out"))
        with pytest.raises(SheetFetchError) as exc_info:
            fetch_raw(GVIZ_URL, timeout=5, sheet_name="Sheet1")
        assert "5 seconds" in str(exc_info.value)

    def test_network_error_raises_network_error(self, httpx_mock: HTTPXMock) -> None:
        import httpx

        httpx_mock.add_exception(httpx.ConnectError("refused"))
        with pytest.raises(NetworkError) as exc_info:
            fetch_raw(GVIZ_URL, sheet_name="Sheet1")
        assert exc_info.value.url == GVIZ_URL

    def test_fetch_error_url_preserved(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, status_code=403)
        with pytest.raises(SheetFetchError) as exc_info:
            fetch_raw(GVIZ_URL)
        assert exc_info.value.url == GVIZ_URL

    def test_sheet_name_in_error_message(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=GVIZ_URL, status_code=404)
        with pytest.raises(SheetFetchError) as exc_info:
            fetch_raw(GVIZ_URL, sheet_name="Sheet1")
        assert "Sheet1" in str(exc_info.value)
