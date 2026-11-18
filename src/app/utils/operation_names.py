#!/usr/bin/env python3
"""
Unique operation names.

Operation names must be unique: each operation owns a folder named after it,
and `Operation.name` is a unique database column. Reusing a name overwrote
the earlier run's files, and the Operations list silently failed to record the
new run. These helpers pick the first free name instead.
"""

from pathlib import Path
from typing import Callable, Iterable, Optional

MAX_SUFFIX = 99


def unique_name(base_name: str, is_taken: Callable[[str], bool]) -> str:
    """Return base_name if it is free, else the first free 'base_name-01', '-02', ...

    Raises:
        ValueError: if base_name and all suffixes up to -99 are taken.
    """
    if not is_taken(base_name):
        return base_name
    for i in range(1, MAX_SUFFIX + 1):
        candidate = f"{base_name}-{i:02d}"
        if not is_taken(candidate):
            return candidate
    raise ValueError(f"No free operation name: '{base_name}' and '{base_name}-01' "
                     f"to '-{MAX_SUFFIX}' are all taken")


def operation_name_checker(service_container, folder_parent: Path,
                           extra_checks: Iterable[Callable[[str], bool]] = ()) -> Callable[[str], bool]:
    """Build an is_taken(name) test for operations whose folder is folder_parent/name.

    A name is taken if that folder exists, an Operations-list record uses it,
    or any extra check (e.g. Elastic records) says so.
    """
    operation_service = service_container.operation_service
    extra_checks = list(extra_checks)

    def is_taken(name: str) -> bool:
        if (Path(folder_parent) / name).exists():
            return True
        if operation_service.get_by_name(name) is not None:
            return True
        return any(check(name) for check in extra_checks)

    return is_taken
