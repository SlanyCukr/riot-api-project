"""Global log capture instance for job logging.

This module provides the global LogCapture instance used by all jobs.
It's in a separate module to avoid circular import issues.
"""

from collections import deque
from typing import Any, MutableMapping


class BoundedLogCapture:
    """Log capture with bounded memory using deque.

    Automatically drops oldest entries when max capacity is reached.
    """

    def __init__(self, maxlen: int = 1000):
        """Initialize with bounded deque that auto-drops oldest entries."""
        self.entries = deque(maxlen=maxlen)

    def __call__(
        self, _: Any, _method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Capture log entry (structlog processor interface) and return unchanged."""
        self.entries.append(event_dict)
        return event_dict


# Global log capture instance with bounded memory (max 1000 entries)
job_log_capture = BoundedLogCapture(maxlen=1000)
