from datetime import datetime, timezone


def utcnow() -> datetime:
    """Fecha y hora UTC sin zona horaria (formato que guardan las columnas DateTime).

    Sustituye a `datetime.utcnow()`, obsoleto desde Python 3.12.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
