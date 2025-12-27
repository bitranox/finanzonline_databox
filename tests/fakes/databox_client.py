"""Fake databox client for testing.

Provides a real in-memory implementation of DataboxPort.
Preferred over mocks because it tests actual behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from finanzonline_databox.domain.models import (
    DataboxDownloadRequest,
    DataboxDownloadResult,
    DataboxListRequest,
    DataboxListResult,
    FinanzOnlineCredentials,
)


@dataclass
class FakeDataboxClient:
    """In-memory fake implementation of DataboxPort.

    Configurable to return success or failure responses.
    Tracks calls for verification without mock assertions.
    """

    list_response: DataboxListResult | None = None
    list_error: Exception | None = None
    download_responses: list[DataboxDownloadResult] = field(
        default_factory=lambda: []  # type: ignore[arg-type]
    )
    download_error: Exception | None = None

    list_calls: list[tuple[str, FinanzOnlineCredentials, DataboxListRequest]] = field(
        default_factory=lambda: []  # type: ignore[arg-type]
    )
    download_calls: list[tuple[str, FinanzOnlineCredentials, DataboxDownloadRequest]] = field(
        default_factory=lambda: []  # type: ignore[arg-type]
    )

    _download_index: int = field(default=0, repr=False)

    def list_entries(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxListRequest,
    ) -> DataboxListResult:
        """Record list call and return configured response."""
        self.list_calls.append((session_id, credentials, request))

        if self.list_error:
            raise self.list_error

        if self.list_response:
            return self.list_response

        # Default empty success response
        from finanzonline_databox.domain.models import DataboxListResult as DLR

        return DLR(rc=0, msg=None, entries=())

    def download_entry(
        self,
        session_id: str,
        credentials: FinanzOnlineCredentials,
        request: DataboxDownloadRequest,
    ) -> DataboxDownloadResult:
        """Record download call and return configured response."""
        self.download_calls.append((session_id, credentials, request))

        if self.download_error:
            raise self.download_error

        if self.download_responses:
            if self._download_index < len(self.download_responses):
                response = self.download_responses[self._download_index]
                self._download_index += 1
                return response
            return self.download_responses[-1]

        # Default success response
        from finanzonline_databox.domain.models import DataboxDownloadResult as DDR

        return DDR(rc=0, msg=None, content=b"fake content")

    @property
    def list_called(self) -> bool:
        """Check if list_entries was called."""
        return len(self.list_calls) > 0

    @property
    def download_called(self) -> bool:
        """Check if download_entry was called."""
        return len(self.download_calls) > 0

    def reset(self) -> None:
        """Clear all recorded calls and reset download index."""
        self.list_calls.clear()
        self.download_calls.clear()
        self._download_index = 0
