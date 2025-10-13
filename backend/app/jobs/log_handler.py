"""Custom logging handler for capturing job execution logs."""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any


class JobLogHandler(logging.Handler):
    """Custom logging handler that captures all log records during job execution.

    This handler captures structured logs from both standard logging and structlog,
    storing them in memory for later persistence to the database.
    """

    def __init__(self, level=logging.DEBUG):
        """Initialize the job log handler.

        Args:
            level: Minimum logging level to capture (default: DEBUG).
        """
        super().__init__(level)
        self.log_records: List[Dict[str, Any]] = []
        self.max_records = 10000  # Prevent memory issues with excessive logging

    def emit(self, record: logging.LogRecord) -> None:
        """Capture a log record.

        Args:
            record: LogRecord to capture.
        """
        try:
            # Prevent infinite recursion if there are any issues
            if len(self.log_records) >= self.max_records:
                return

            # Extract log data
            log_entry = {
                "timestamp": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }

            # Add structured logging context if available (from structlog)
            # structlog stores additional context in record.__dict__
            if hasattr(record, "_context"):
                log_entry["context"] = record._context
            elif hasattr(record, "event_dict"):
                # Alternative structlog format
                log_entry["context"] = record.event_dict

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.format_exception(record.exc_info)

            # Add file/line info for debugging
            log_entry["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

            self.log_records.append(log_entry)

        except Exception:
            # Silently ignore errors in log handler to avoid breaking job execution
            pass

    def format_exception(self, exc_info) -> Dict[str, Any]:
        """Format exception information.

        Args:
            exc_info: Exception info tuple.

        Returns:
            Formatted exception data.
        """
        import traceback

        exc_type, exc_value, exc_tb = exc_info
        return {
            "type": exc_type.__name__ if exc_type else None,
            "message": str(exc_value) if exc_value else None,
            "traceback": traceback.format_exception(exc_type, exc_value, exc_tb),
        }

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get captured log records.

        Returns:
            List of captured log records.
        """
        return self.log_records.copy()

    def clear_logs(self) -> None:
        """Clear captured log records."""
        self.log_records.clear()

    def get_log_summary(self) -> Dict[str, Any]:
        """Get a summary of captured logs.

        Returns:
            Summary including counts by level and recent errors.
        """
        summary = {
            "total_logs": len(self.log_records),
            "by_level": {},
            "errors": [],
            "warnings": [],
        }

        for record in self.log_records:
            level = record["level"]
            summary["by_level"][level] = summary["by_level"].get(level, 0) + 1

            if level == "ERROR":
                summary["errors"].append(
                    {
                        "timestamp": record["timestamp"],
                        "message": record["message"],
                        "context": record.get("context", {}),
                    }
                )
            elif level == "WARNING":
                summary["warnings"].append(
                    {
                        "timestamp": record["timestamp"],
                        "message": record["message"],
                        "context": record.get("context", {}),
                    }
                )

        return summary


class StructlogJobProcessor:
    """Structlog processor that captures logs to JobLogHandler.

    This processor works with structlog's pipeline to ensure structured
    logs are also captured by our JobLogHandler.
    """

    def __init__(self, handler: JobLogHandler):
        """Initialize the processor.

        Args:
            handler: JobLogHandler to send logs to.
        """
        self.handler = handler

    def __call__(self, logger, method_name, event_dict):
        """Process a structlog event.

        Args:
            logger: Logger instance.
            method_name: Log method name.
            event_dict: Event dictionary.

        Returns:
            Event dictionary (unchanged).
        """
        try:
            # Create a synthetic LogRecord for the handler
            level_mapping = {
                "debug": logging.DEBUG,
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL,
            }

            level = level_mapping.get(method_name, logging.INFO)

            # Extract the main message
            message = event_dict.get("event", "")

            # Create a LogRecord
            record = logging.LogRecord(
                name=logger.name if hasattr(logger, "name") else "structlog",
                level=level,
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None,
            )

            # Attach the full event dict as context
            record._context = {k: v for k, v in event_dict.items() if k != "event"}

            # Send to handler
            self.handler.emit(record)

        except Exception:
            # Silently ignore errors
            pass

        # Return event_dict unchanged for other processors
        return event_dict
