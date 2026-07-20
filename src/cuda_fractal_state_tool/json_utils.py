from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Tuple


@dataclass
class DuplicateKeyError(ValueError):
    path: str
    key: str

    def __str__(self) -> str:
        location = self.path or "$"
        return f"Duplicate JSON key '{self.key}' at {location}"


class _DuplicateKeyDetector(dict):
    pass


def _object_pairs_hook_factory(path_stack: list[str]):
    def hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        seen: set[str] = set()
        current_path = ".".join(path_stack)
        for key, value in pairs:
            if key in seen:
                raise DuplicateKeyError(current_path, key)
            seen.add(key)
            result[key] = value
        return result

    return hook


def loads_no_duplicates(text: str) -> Any:
    path_stack: list[str] = []

    class Decoder(json.JSONDecoder):
        def __init__(self) -> None:
            super().__init__(object_pairs_hook=_object_pairs_hook_factory(path_stack))

    return json.loads(text, cls=Decoder)


def dumps_pretty(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
