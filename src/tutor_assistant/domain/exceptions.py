"""Domain exceptions."""

from __future__ import annotations


class StudentNameTaken(Exception):
    """Raised when a student with this name already exists for the tutor."""


class StudentNotFound(Exception):
    """Raised when the requested student does not exist."""


class SlotConflict(Exception):
    """Raised when new slots overlap with existing schedule."""

    def __init__(self, conflicts: list[str]) -> None:
        self.conflicts = conflicts
        super().__init__("\n".join(conflicts))
