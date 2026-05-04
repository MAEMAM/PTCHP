"""Common adapter interface — every platform integration implements this."""
from __future__ import annotations
import abc
from datetime import datetime
from typing import Optional

from models import Mention


class BaseAdapter(abc.ABC):
    """Each platform integration subclasses this."""

    name: str = "base"
    rate_limit_per_minute: int = 60

    @abc.abstractmethod
    async def fetch(
        self,
        keywords: list[str],
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Mention]:
        """Fetch recent mentions matching keywords. Implementations must
        respect platform rate limits and return normalized Mention objects."""
        ...

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Return True if all required credentials are present."""
        ...

    async def health(self) -> dict:
        """Lightweight check — adapter pings its own auth endpoint."""
        return {
            "adapter": self.name,
            "configured": self.is_configured(),
            "rate_limit": self.rate_limit_per_minute,
        }
