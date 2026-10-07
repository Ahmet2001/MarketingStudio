import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar


T = TypeVar("T")

RETRYABLE_STATUS_CODES = {408, 409, 425, 429}
RETRYABLE_ERROR_NAMES = (
    "connectionerror",
    "connecterror",
    "networkerror",
    "pooltimeout",
    "protocolerror",
    "proxyerror",
    "readerror",
    "readtimeout",
    "remotedisconnected",
    "serviceunavailable",
    "timeout",
    "transporterror",
    "writeerror",
    "writetimeout",
)
RETRYABLE_MESSAGE_PARTS = (
    "connection reset",
    "connection refused",
    "connection aborted",
    "rate limit",
    "resource exhausted",
    "server overloaded",
    "service unavailable",
    "temporarily unavailable",
    "temporary failure",
    "timed out",
    "too many requests",
    "try again",
)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 6
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter_ratio: float = 0.20

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("Retry max_attempts must be at least 1.")
        if self.base_delay < 0:
            raise ValueError("Retry base_delay cannot be negative.")
        if self.max_delay < 0:
            raise ValueError("Retry max_delay cannot be negative.")
        if self.jitter_ratio < 0:
            raise ValueError("Retry jitter_ratio cannot be negative.")


def _integer_status(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def api_status_code(error: Exception) -> int | None:
    for attribute in ("status_code", "status", "code"):
        status = _integer_status(getattr(error, attribute, None))
        if status is not None:
            return status

    response = getattr(error, "response", None)
    return _integer_status(getattr(response, "status_code", None))


def _error_headers(error: Exception) -> dict[str, str]:
    sources = [
        getattr(error, "headers", None),
        getattr(getattr(error, "response", None), "headers", None),
    ]
    for source in sources:
        if source:
            try:
                return {str(key).lower(): str(value) for key, value in source.items()}
            except (AttributeError, TypeError, ValueError):
                continue
    return {}


def _duration_in_seconds(value: str, unit: str) -> float:
    duration = float(value)
    normalized_unit = unit.lower()
    if normalized_unit.startswith("ms"):
        return duration / 1000
    if normalized_unit.startswith("m") and not normalized_unit.startswith("ms"):
        return duration * 60
    return duration


def retry_after_seconds(error: Exception) -> float | None:
    retry_after = _error_headers(error).get("retry-after")
    if retry_after:
        try:
            return max(0.0, float(retry_after.strip()))
        except ValueError:
            pass

    message_parts = [
        str(error),
        str(getattr(error, "detail", "") or ""),
        str(getattr(error, "message", "") or ""),
        str(getattr(error, "body", "") or ""),
    ]
    message = " ".join(message_parts)
    unit_pattern = r"(ms|milliseconds?|s|secs?|seconds?|m|mins?|minutes?)"
    patterns = (
        rf"resets?\s+in\s*~?\s*(\d+(?:\.\d+)?)\s*{unit_pattern}",
        rf"retry\s+(?:in|after)\s*~?\s*(\d+(?:\.\d+)?)\s*{unit_pattern}",
    )
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return max(0.0, _duration_in_seconds(match.group(1), match.group(2)))
    return None


def is_retryable_api_error(error: Exception) -> bool:
    status = api_status_code(error)
    if status in RETRYABLE_STATUS_CODES or (status is not None and 500 <= status <= 599):
        return True
    if status is not None:
        return False

    error_names = " ".join(
        error_class.__name__.lower() for error_class in type(error).mro()
    )
    if any(name in error_names for name in RETRYABLE_ERROR_NAMES):
        return True

    message = str(error).lower()
    return any(part in message for part in RETRYABLE_MESSAGE_PARTS)


def _error_summary(error: Exception, max_length: int = 280) -> str:
    summary = re.sub(r"\s+", " ", str(error)).strip()
    if len(summary) > max_length:
        return summary[: max_length - 1] + "…"
    return summary


def call_with_retry(
    operation: Callable[[], T],
    *,
    label: str,
    policy: RetryPolicy,
) -> T:
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return operation()
        except Exception as error:
            can_retry = (
                attempt < policy.max_attempts and is_retryable_api_error(error)
            )
            if not can_retry:
                raise

            retry_after = retry_after_seconds(error)
            if retry_after is not None:
                delay = min(policy.max_delay, retry_after + 0.25)
            else:
                exponential_delay = policy.base_delay * (2 ** (attempt - 1))
                capped_delay = min(policy.max_delay, exponential_delay)
                jitter = capped_delay * policy.jitter_ratio * random.random()
                delay = min(policy.max_delay, capped_delay + jitter)

            status = api_status_code(error)
            status_text = f"HTTP {status}; " if status is not None else ""
            next_attempt = attempt + 1
            print(
                f"{label} failed ({status_text}{_error_summary(error)}). "
                f"Retrying in {delay:.1f}s "
                f"(attempt {next_attempt}/{policy.max_attempts})..."
            )
            time.sleep(delay)

    raise AssertionError("Retry loop exited unexpectedly.")
