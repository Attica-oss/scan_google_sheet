"""Tests for the custom exception hierarchy."""

# import pytest

from scan_google_sheet.exceptions import (
    ConfigurationError,
    NetworkError,
    ReadSheetError,
    SheetFetchError,
    SheetParseError,
    SheetURLError,
)


class TestHierarchy:
    """All custom exceptions must be ReadSheetError subclasses."""

    def test_sheet_url_error(self) -> None:
        assert issubclass(SheetURLError, ReadSheetError)

    def test_sheet_fetch_error(self) -> None:
        assert issubclass(SheetFetchError, ReadSheetError)

    def test_sheet_parse_error(self) -> None:
        assert issubclass(SheetParseError, ReadSheetError)

    def test_network_error(self) -> None:
        assert issubclass(NetworkError, ReadSheetError)

    def test_configuration_error(self) -> None:
        assert issubclass(ConfigurationError, ReadSheetError)


class TestReadSheetError:
    def test_message(self) -> None:
        err = ReadSheetError("something failed")
        assert str(err) == "something failed"

    def test_cause_preserved(self) -> None:
        original = ValueError("original")
        err = ReadSheetError("wrapped", cause=original)
        assert err.cause is original
        assert err.__cause__ is original

    def test_repr_without_cause(self) -> None:
        err = ReadSheetError("oops")
        assert repr(err) == "ReadSheetError('oops')"

    def test_repr_with_cause(self) -> None:
        cause = ValueError("bad")
        err = ReadSheetError("oops", cause=cause)
        assert "cause=" in repr(err)


class TestSheetURLError:
    def test_raw_attribute(self) -> None:
        err = SheetURLError("bad url", raw="not-a-url")
        assert err.raw == "not-a-url"

    def test_raw_in_repr(self) -> None:
        err = SheetURLError("bad url", raw="not-a-url")
        assert "raw=" in repr(err)

    def test_raw_optional(self) -> None:
        err = SheetURLError("bad url")
        assert err.raw is None


class TestSheetFetchError:
    def test_status_code(self) -> None:
        err = SheetFetchError("failed", url="https://x.com", status_code=404)
        assert err.status_code == 404

    def test_is_auth_error_401(self) -> None:
        err = SheetFetchError("forbidden", status_code=401)
        assert err.is_auth_error is True

    def test_is_auth_error_403(self) -> None:
        err = SheetFetchError("forbidden", status_code=403)
        assert err.is_auth_error is True

    def test_is_not_found(self) -> None:
        err = SheetFetchError("missing", status_code=404)
        assert err.is_not_found is True

    def test_is_auth_error_false_for_404(self) -> None:
        err = SheetFetchError("missing", status_code=404)
        assert err.is_auth_error is False

    def test_no_status_code(self) -> None:
        err = SheetFetchError("timeout")
        assert err.status_code is None
        assert err.is_auth_error is False
        assert err.is_not_found is False


class TestSheetParseError:
    def test_column_attribute(self) -> None:
        err = SheetParseError("type mismatch", column="amount")
        assert err.column == "amount"

    def test_from_polars(self) -> None:
        from polars.exceptions import SchemaError

        original = SchemaError("bad schema")
        err = SheetParseError.from_polars(original, step="parse_csv")
        assert isinstance(err, SheetParseError)
        assert err.cause is original
        assert "parse_csv" in str(err)


class TestMatchCase:
    """Verify exceptions work correctly with match/case."""

    def test_match_fetch_error_by_status(self) -> None:
        err = SheetFetchError("not public", status_code=401)
        matched = False
        match err:
            case SheetFetchError() if err.is_auth_error:
                matched = True
        assert matched

    def test_match_url_error_raw(self) -> None:
        err = SheetURLError("bad", raw="garbage")
        captured = None
        match err:
            case SheetURLError(raw=r):
                captured = r
        assert captured == "garbage"
