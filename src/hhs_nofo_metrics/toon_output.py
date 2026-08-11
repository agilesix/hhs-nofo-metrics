"""Small TOON 4.1 encoder for the CLI's JSON-shaped output.

The product result file remains JSON. This module exists only at the terminal
output boundary so agent callers receive compact structured receipts, lists,
details, and errors without adding an external runtime dependency.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import TypeAlias

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | Mapping[str, "JsonValue"] | Sequence["JsonValue"]

_UNQUOTED_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_NUMERIC_LIKE_RE = re.compile(
    r"^[+-]?[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?$", re.IGNORECASE
)


def _escape(value: str) -> str:
    pieces: list[str] = []
    for character in value:
        codepoint = ord(character)
        if character == "\\":
            pieces.append("\\\\")
        elif character == '"':
            pieces.append('\\"')
        elif character == "\n":
            pieces.append("\\n")
        elif character == "\r":
            pieces.append("\\r")
        elif character == "\t":
            pieces.append("\\t")
        elif codepoint < 0x20:
            pieces.append(f"\\u{codepoint:04x}")
        elif 0xD800 <= codepoint <= 0xDFFF:
            raise ValueError("TOON cannot encode an unpaired Unicode surrogate")
        else:
            pieces.append(character)
    return "".join(pieces)


def _encode_key(value: str) -> str:
    if _UNQUOTED_KEY_RE.fullmatch(value):
        return value
    return f'"{_escape(value)}"'


def _encode_string(value: str, *, delimiter: str = ",") -> str:
    must_quote = (
        not value
        or value[:1].isspace()
        or value[-1:].isspace()
        or value in {"true", "false", "null"}
        or _NUMERIC_LIKE_RE.fullmatch(value) is not None
        or any(character in value for character in (":", '"', "\\", "[", "]", "{", "}"))
        or any(ord(character) < 0x20 for character in value)
        or delimiter in value
        or value.startswith(("-", "#"))
    )
    return f'"{_escape(value)}"' if must_quote else value


def _encode_number(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(value):
        return "null"
    if value == 0:
        return "0"
    absolute = abs(value)
    if 1e-6 <= absolute < 1e21:
        result = format(Decimal(str(value)), "f")
        if "." in result:
            result = result.rstrip("0").rstrip(".")
        return result
    mantissa, exponent = format(value, ".15e").split("e")
    mantissa = mantissa.rstrip("0").rstrip(".")
    return f"{mantissa}e{int(exponent):+d}"


def _encode_primitive(value: JsonPrimitive, *, delimiter: str = ",") -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _encode_number(value)
    if isinstance(value, str):
        return _encode_string(value, delimiter=delimiter)
    raise TypeError(f"Unsupported TOON primitive: {type(value).__name__}")


def _is_primitive(value: object) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _uniform_primitive_objects(
    values: Sequence[JsonValue],
) -> tuple[str, ...] | None:
    if not values or not all(isinstance(item, Mapping) and item for item in values):
        return None
    first = values[0]
    assert isinstance(first, Mapping)
    fields = tuple(first)
    expected = set(fields)
    for item in values:
        assert isinstance(item, Mapping)
        if set(item) != expected or not all(
            _is_primitive(item[field]) for field in fields
        ):
            return None
    return fields


def _uniform_primitive_object_values(
    value: Mapping[str, JsonValue],
) -> tuple[str, ...] | None:
    if len(value) < 2:
        return None
    return _uniform_primitive_objects(tuple(value.values()))


def _encode_field(
    key: str,
    value: JsonValue,
    *,
    depth: int,
    first_item_field: bool = False,
) -> list[str]:
    indentation = "  " * depth
    prefix = f"{indentation}- " if first_item_field else indentation
    encoded_key = _encode_key(key)
    content_depth = depth + (2 if first_item_field else 1)

    if _is_primitive(value):
        return [f"{prefix}{encoded_key}: {_encode_primitive(value)}"]
    if isinstance(value, Mapping):
        keyed_fields = _uniform_primitive_object_values(value)
        if keyed_fields is not None:
            header = ",".join(_encode_key(field) for field in keyed_fields)
            lines = [f"{prefix}{encoded_key}[{len(value)}:]{{{header}}}:"]
            for entry_key, row in value.items():
                assert isinstance(row, Mapping)
                cells = ",".join(
                    _encode_primitive(row[field], delimiter=",")
                    for field in keyed_fields
                )
                lines.append(f"{'  ' * content_depth}{_encode_key(entry_key)}: {cells}")
            return lines
        lines = [f"{prefix}{encoded_key}:"]
        for nested_key, nested_value in value.items():
            lines.extend(
                _encode_field(
                    nested_key,
                    nested_value,
                    depth=content_depth,
                )
            )
        return lines
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = tuple(value)
        if not items:
            return [f"{prefix}{encoded_key}: []"]
        if all(_is_primitive(item) for item in items):
            encoded = ",".join(_encode_primitive(item, delimiter=",") for item in items)
            return [f"{prefix}{encoded_key}[{len(items)}]: {encoded}"]
        fields = _uniform_primitive_objects(items)
        if fields is not None:
            header = ",".join(_encode_key(field) for field in fields)
            lines = [f"{prefix}{encoded_key}[{len(items)}]{{{header}}}:"]
            for item in items:
                assert isinstance(item, Mapping)
                cells = ",".join(
                    _encode_primitive(item[field], delimiter=",") for field in fields
                )
                lines.append(f"{'  ' * content_depth}{cells}")
            return lines
        lines = [f"{prefix}{encoded_key}[{len(items)}]:"]
        for item in items:
            lines.extend(_encode_list_item(item, depth=content_depth))
        return lines
    raise TypeError(f"Unsupported TOON value: {type(value).__name__}")


def _encode_list_item(value: JsonValue, *, depth: int) -> list[str]:
    indentation = "  " * depth
    if _is_primitive(value):
        return [f"{indentation}- {_encode_primitive(value)}"]
    if isinstance(value, Mapping):
        if not value:
            return [f"{indentation}-"]
        first_key, first_value = next(iter(value.items()))
        lines = _encode_field(
            first_key,
            first_value,
            depth=depth,
            first_item_field=True,
        )
        for key, item in tuple(value.items())[1:]:
            lines.extend(_encode_field(key, item, depth=depth + 1))
        return lines
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = tuple(value)
        if not items:
            return [f"{indentation}- [0]:"]
        if all(_is_primitive(item) for item in items):
            encoded = ",".join(_encode_primitive(item, delimiter=",") for item in items)
            return [f"{indentation}- [{len(items)}]: {encoded}"]
        lines = [f"{indentation}- [{len(items)}]:"]
        for item in items:
            lines.extend(_encode_list_item(item, depth=depth + 1))
        return lines
    raise TypeError(f"Unsupported TOON list item: {type(value).__name__}")


def encode_toon(value: JsonValue) -> str:
    """Encode one JSON-shaped value as canonical-enough TOON 4.1 terminal data."""

    if _is_primitive(value):
        return _encode_primitive(value)
    if isinstance(value, Mapping):
        keyed_fields = _uniform_primitive_object_values(value)
        if keyed_fields is not None:
            header = ",".join(_encode_key(field) for field in keyed_fields)
            lines = [f"[{len(value)}:]{{{header}}}:"]
            for entry_key, row in value.items():
                assert isinstance(row, Mapping)
                cells = ",".join(
                    _encode_primitive(row[field], delimiter=",")
                    for field in keyed_fields
                )
                lines.append(f"  {_encode_key(entry_key)}: {cells}")
            return "\n".join(lines)
        lines: list[str] = []
        for key, item in value.items():
            lines.extend(_encode_field(key, item, depth=0))
        return "\n".join(lines)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = tuple(value)
        if not items:
            return "[]"
        if all(_is_primitive(item) for item in items):
            return f"[{len(items)}]: " + ",".join(
                _encode_primitive(item, delimiter=",") for item in items
            )
        fields = _uniform_primitive_objects(items)
        if fields is not None:
            header = ",".join(_encode_key(field) for field in fields)
            lines = [f"[{len(items)}]{{{header}}}:"]
            for item in items:
                assert isinstance(item, Mapping)
                lines.append(
                    "  "
                    + ",".join(
                        _encode_primitive(item[field], delimiter=",")
                        for field in fields
                    )
                )
            return "\n".join(lines)
        lines = [f"[{len(items)}]:"]
        for item in items:
            lines.extend(_encode_list_item(item, depth=1))
        return "\n".join(lines)
    raise TypeError(f"Unsupported TOON root: {type(value).__name__}")


__all__ = ["encode_toon"]
