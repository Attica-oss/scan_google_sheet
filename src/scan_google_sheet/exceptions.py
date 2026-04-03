"""Custom exceptions for read-sheet.

Three failure domains, one base:

    ReadSheetError          ← base, always carries optional ``cause``
    ├── SheetURLError       ← malformed URL or unextractable sheet ID
    ├── SheetFetchError     ← HTTP / network failure, carries ``url`` + ``status_code``
    └── SheetParseError     ← CSV or Polars schema/parse failure, carries ``column``

All subclasses preserve the original exception via ``cause`` / ``__cause__``
so tracebacks remain intact and ``match``/``case`` branches can inspect them.
"""

from __future__ import annotations

from polars.exceptions import (
    ColumnNotFoundError,
    ComputeError,
    DuplicateError,
    InvalidOperationError,
    NoDataError,
    PolarsError,
    SchemaError,
    ShapeError,
)

__all__ = [
    "ConfigurationError",
    "NetworkError",
    "ReadSheetError",
    "SheetFetchError",
    "SheetParseError",
    "SheetURLError",
]


# ── Base ──────────────────────────────────────────────────────────────────────


class ReadSheetError(Exception):
    """Base exception for all read-sheet errors.

    Every subclass carries an optional ``cause`` that preserves the original
    exception, making it safe to use inside ``match``/``case`` without losing
    the underlying traceback.

    Examples:
        >>> raise ReadSheetError("something went wrong")
        ReadSheetError('something went wrong')

        >>> try:
        ...     int("bad")
        ... except ValueError as e:
        ...     raise ReadSheetError("unexpected value", cause=e) from e
    """

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause

    def __repr__(self) -> str:
        if self.cause:
            return f"{type(self).__name__}({self.args[0]!r}, cause={self.cause!r})"
        return f"{type(self).__name__}({self.args[0]!r})"


# ── Subclasses ────────────────────────────────────────────────────────────────


class SheetURLError(ReadSheetError):
    """Raised when a Google Sheets URL or ID cannot be parsed.

    Carries the ``raw`` value that failed so callers can log or surface it
    without reparsing the message string.

    Examples:
        >>> err = SheetURLError("No sheet ID found", raw="not-a-url")
        >>> err.raw
        'not-a-url'
    """

    def __init__(
        self,
        message: str,
        *,
        raw: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.raw = raw

    def __repr__(self) -> str:
        parts = [repr(self.args[0])]
        if self.raw is not None:
            parts.append(f"raw={self.raw!r}")
        if self.cause is not None:
            parts.append(f"cause={self.cause!r}")
        return f"SheetURLError({', '.join(parts)})"


class SheetFetchError(ReadSheetError):
    """Raised when the HTTP request to Google Sheets fails.

    Carries the ``url`` that was requested and the HTTP ``status_code`` when
    one is available (``None`` for pure network errors).

    Examples:
        >>> err = SheetFetchError("Sheet is not public", url="https://...", status_code=401)
        >>> err.status_code
        401
        >>> err.is_auth_error
        True
    """

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status_code: int | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.url = url
        self.status_code = status_code

    @property
    def is_auth_error(self) -> bool:
        """True when the sheet is not publicly accessible (HTTP 401/403)."""
        return self.status_code in (401, 403)

    @property
    def is_not_found(self) -> bool:
        """True when the sheet ID does not exist (HTTP 404)."""
        return self.status_code == 404

    def __repr__(self) -> str:
        parts = [repr(self.args[0])]
        if self.url is not None:
            parts.append(f"url={self.url!r}")
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code!r}")
        if self.cause is not None:
            parts.append(f"cause={self.cause!r}")
        return f"SheetFetchError({', '.join(parts)})"


class SheetParseError(ReadSheetError):
    """Raised when CSV or Polars parsing fails after a successful fetch.

    Carries the ``column`` name when the failure can be attributed to a
    specific field, and wraps Polars exceptions via ``from_polars()``.

    Examples:
        >>> err = SheetParseError("Type mismatch", column="amount")
        >>> err.column
        'amount'

        >>> from polars.exceptions import SchemaError
        >>> err = SheetParseError.from_polars(SchemaError("bad schema"), step="parse_csv")
        >>> type(err)
        <class 'SheetParseError'>
        >>> err.cause
        SchemaError('bad schema')
    """

    def __init__(
        self,
        message: str,
        *,
        column: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.column = column

    @classmethod
    def from_polars(cls, error: PolarsError, step: str) -> SheetParseError:
        """Wrap a raw Polars exception with step context.

        Args:
            error: The original Polars exception.
            step:  Human-readable label for the pipeline step that failed.

        Returns:
            A ``SheetParseError`` with ``cause`` set to the original error.
        """
        return cls(f"{step}: {error}", cause=error)

    def __repr__(self) -> str:
        parts = [repr(self.args[0])]
        if self.column is not None:
            parts.append(f"column={self.column!r}")
        if self.cause is not None:
            parts.append(f"cause={self.cause!r}")
        return f"SheetParseError({', '.join(parts)})"


class NetworkError(ReadSheetError):
    """Raised when a connection or transport-level failure occurs.

    Distinct from ``SheetFetchError`` (which implies a completed HTTP round-trip
    with a status code). ``NetworkError`` fires when no response is received at
    all — DNS failure, refused connection, proxy error, etc.

    Examples:
        >>> err = NetworkError("DNS resolution failed", url="https://docs.google.com/...")
        >>> err.url
        'https://docs.google.com/...'
    """

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.url = url

    def __repr__(self) -> str:
        parts = [repr(self.args[0])]
        if self.url is not None:
            parts.append(f"url={self.url!r}")
        if self.cause is not None:
            parts.append(f"cause={self.cause!r}")
        return f"NetworkError({', '.join(parts)})"


class ConfigurationError(ReadSheetError):
    """Raised when ``scan_google_sheet`` is called with invalid arguments.

    Typically fired when both ``sheet_id`` and ``url`` are provided, or
    neither is provided.

    Examples:
        >>> raise ConfigurationError("Provide either sheet_id or url, not both")
    """


# ── Polars → SheetParseError mapping ─────────────────────────────────────────

# Used internally by SheetParseError.from_polars() and parse.py.
_POLARS_PARSE_ERRORS: frozenset[type[PolarsError]] = frozenset(
    {
        SchemaError,
        ColumnNotFoundError,
        DuplicateError,
        ComputeError,
        InvalidOperationError,
        ShapeError,
        NoDataError,
    }
)
