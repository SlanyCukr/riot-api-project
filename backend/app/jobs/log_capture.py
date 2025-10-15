"""Global log capture instance for job logging.

This module provides the global LogCapture instance used by all jobs.
It's in a separate module to avoid circular import issues.
"""

from structlog.testing import LogCapture

# Global LogCapture instance for capturing job logs
job_log_capture = LogCapture()
