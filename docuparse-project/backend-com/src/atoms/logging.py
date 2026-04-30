"""Structured logging configuration for KAI Mind.

Uses structlog for structured, contextual logging.
"""
import logging
import os
import sys
from typing import Any

import structlog
from structlog.typing import EventDict
from structlog.typing import WrappedLogger


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add application context to log entries."""
    event_dict["app"] = "atoms"
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_logs: bool = False,
    console_logs: bool = False,
    include_timestamp: bool = True,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output logs as JSON (for production)
        console_logs: If True, output logs to the console (for development)
        include_timestamp: If True, include timestamp in logs

    """
    # Configure standard library logging
    # Set root logger to WARNING to suppress dependency logs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.WARNING,
    )

    # Set kai_mind logger to the desired level
    kai_mind_logger = logging.getLogger("kai_mind")
    kai_mind_logger.setLevel(getattr(logging, level.upper()))

    # Build processor chain
    processors = [
        structlog.contextvars.merge_contextvars,
        add_app_context,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]

    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    # Add exception formatter
    processors.append(structlog.processors.format_exc_info)

    # Choose renderer based on environment
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
        logger_factory = structlog.PrintLoggerFactory()
    elif console_logs:
        processors.append(structlog.dev.ConsoleRenderer())
        logger_factory = structlog.PrintLoggerFactory()
    else:
        processors.append(structlog.processors.KeyValueRenderer())
        logger_factory = structlog.PrintLoggerFactory(file=open(os.devnull, "w"))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=logger_factory,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance

    """
    # Use atoms as the base logger name to respect our logging configuration
    if name:
        logger_name = f"atoms.{name}"
    else:
        logger_name = "atoms"

    return structlog.get_logger(logger_name)


# Example usage in other modules:
# from atoms.logging import get_logger
# logger = get_logger(__name__)
#
# logger.info("Processing message", user_id=user_id, session_id=session_id)
# logger.error("Failed to process", error=str(e), session_id=session_id)
