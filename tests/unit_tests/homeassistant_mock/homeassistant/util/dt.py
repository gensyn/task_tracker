from datetime import datetime, timezone

UTC = timezone.utc


def now():
    """Return the current datetime in UTC (mirrors homeassistant.util.dt.now)."""
    return datetime.now(UTC)
