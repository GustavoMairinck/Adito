"""JSON das respostas, com as mesmas conversões que o DRF fazia (Decimal vira número, datas viram ISO)."""
import json
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

import numpy as np


def _default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            text = value.astimezone(timezone.utc).isoformat()
            return text[:-6] + "Z" if text.endswith("+00:00") else text
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode()
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return str(value)


def dumps(obj) -> str:
    """Uma linha só (o protocolo separa mensagens por \\n), sem escapar acentos."""
    return json.dumps(obj, default=_default, ensure_ascii=False, separators=(",", ":"))
