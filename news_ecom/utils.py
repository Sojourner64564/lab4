from datetime import datetime, timezone


def parse_iso(value):
    """'2024-05-01T10:00:00.000Z' -> aware datetime (UTC). None при ошибке."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
