"""FinanzOnline SOAP client adapters.

Purpose
-------
Implement SessionPort and DataboxPort using zeep SOAP client
to communicate with BMF FinanzOnline web services.

Contents
--------
* :class:`.session_client.FinanzOnlineSessionClient` - Session management
* :class:`.databox_client.DataboxClient` - DataBox operations

System Role
-----------
Adapters layer - implements application ports with actual SOAP calls.
"""

from __future__ import annotations

from .databox_client import DataboxClient
from .session_client import FinanzOnlineSessionClient

__all__ = [
    "DataboxClient",
    "FinanzOnlineSessionClient",
]
