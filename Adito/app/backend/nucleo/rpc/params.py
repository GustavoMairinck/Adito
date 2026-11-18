"""
Validação de parâmetros com as mensagens que o DRF devolvia ({"campo": ["mensagem"]}),
para o front tratar erros do mesmo jeito.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .errors import bad_request

REQUIRED = "This field is required."
_MISSING = object()


@dataclass
class Field:
    required: bool = False
    default: Any = _MISSING
    allow_null: bool = False

    def convert(self, value):
        return value


@dataclass
class Str(Field):
    max_length: int | None = None
    allow_blank: bool = True
    trim: bool = True

    def convert(self, value):
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError("Not a valid string.")
        value = str(value)
        if self.trim:
            value = value.strip()
        if not value and not self.allow_blank:
            raise ValueError("This field may not be blank.")
        if self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"Ensure this field has no more than {self.max_length} characters.")
        return value


@dataclass
class Int(Field):
    min_value: int | None = None

    def convert(self, value):
        try:
            if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
                raise ValueError
            value = int(str(value).strip())
        except (TypeError, ValueError):
            raise ValueError("A valid integer is required.") from None
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Ensure this value is greater than or equal to {self.min_value}.")
        return value


@dataclass
class Uuid(Field):
    def convert(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError, AttributeError):
            raise ValueError("Must be a valid UUID.") from None


@dataclass
class Choice(Field):
    choices: tuple = ()

    def convert(self, value):
        for choice in self.choices:
            if str(choice) == str(value):
                return choice
        raise ValueError(f'"{value}" is not a valid choice.')


@dataclass
class Bool(Field):
    def convert(self, value):
        if value in (True, "true", "True", "1", 1, "yes", "on"):
            return True
        if value in (False, "false", "False", "0", 0, "no", "off"):
            return False
        raise ValueError("Must be a valid boolean.")


def validate(spec: dict[str, Field], data: dict, partial: bool = False) -> dict:
    """Valida `data` contra `spec`. Campos ausentes recebem o default; `partial` não exige nada."""
    out, errors = {}, {}
    for name, field in spec.items():
        if name not in data:
            if field.required and not partial:
                errors[name] = [REQUIRED]
            elif field.default is not _MISSING and not partial:
                out[name] = field.default
            continue
        value = data[name]
        if value is None:
            if field.allow_null:
                out[name] = None
            else:
                errors[name] = ["This field may not be null."]
            continue
        try:
            out[name] = field.convert(value)
        except ValueError as exc:
            errors[name] = [str(exc)]
    if errors:
        raise bad_request(errors)
    return out
