"""In-memory fake implementations for testing.

Provides real behavior without external dependencies.
These fakes are preferred over mocks because they:
- Test actual logic and data flow
- Are more reliable indicators of correctness
- Don't require asserting mock calls
"""

from __future__ import annotations

from .databox_client import FakeDataboxClient
from .session_client import FakeSessionClient

__all__ = [
    "FakeSessionClient",
    "FakeDataboxClient",
]
