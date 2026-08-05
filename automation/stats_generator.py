"""Generate aggregate LeetCode statistics from a metadata JSON document.

This module does not scan repositories or render README files.  Callers choose
the output path explicitly, preventing accidental writes to LeetHub-managed
files.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import logging
from types import MappingProxyType
from typing import Any

from .utils import format_date, get_logger, read_json, write_json_safely


_DIFFICULTIES: tuple[str, ...] = ("Easy", "Medium", "Hard")
_REQUIRED_LANGUAGES: tuple[str, ...] = ("Python", "C++", "MySQL")


@dataclass(frozen=True, slots=True)
class MetadataProblem:
    """The subset of one metadata problem record used for aggregation."""

    number: int
    name: str
    difficulty: str | None
    topics: tuple[str, ...]
    languages: tuple[str, ...]
    folder: str
    leetcode_link: str | None
    last_modified: str


@dataclass(frozen=True, slots=True)
class DistributionEntry:
    """A count and percentage for one statistics dimension."""

    name: str
    count: int
    percentage: float

    def to_dict(self, key: str) -> dict[str, str | int | float]:
        """Return a JSON-compatible distribution entry using *key* as its name."""

        return {key: self.name, "count": self.count, "percentage": self.percentage}


@dataclass(frozen=True, slots=True)
class RecentlySolvedProblem:
    """A compact recent-solution record included in statistics output."""

    number: int
    name: str
    folder: str
    last_modified: str
    leetcode_link: str | None

    def to_dict(self) -> dict[str, str | int | None]:
        """Return a JSON-compatible recent-solution record."""

        return {
            "number": self.number,
            "name": self.name,
            "folder": self.folder,
            "last_modified": self.last_modified,
            "leetcode_link": self.leetcode_link,
        }


@dataclass(frozen=True, slots=True)
class StatisticsDocument:
    """Clean, serializable aggregate statistics derived from metadata."""

    generated_at: str
    total_solved: int
    easy: int
    medium: int
    hard: int
    python_count: int
    cpp_count: int
    mysql_count: int
    topic_counts: Mapping[str, int]
    recently_solved: tuple[RecentlySolvedProblem, ...]
    language_distribution: tuple[DistributionEntry, ...]
    difficulty_distribution: tuple[DistributionEntry, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the clean JSON document requested by the statistics contract."""

        return {
            "generated_at": self.generated_at,
            "total_solved": self.total_solved,
            "easy": self.easy,
            "medium": self.medium,
            "hard": self.hard,
            "python_count": self.python_count,
            "cpp_count": self.cpp_count,
            "mysql_count": self.mysql_count,
            "topic_counts": dict(self.topic_counts),
            "recently_solved": [entry.to_dict() for entry in self.recently_solved],
            "language_distribution": [
                entry.to_dict("language") for entry in self.language_distribution
            ],
            "difficulty_distribution": [
                entry.to_dict("difficulty") for entry in self.difficulty_distribution
            ],
        }


def generate_statistics(
    metadata_path: Path,
    *,
    recent_limit: int = 10,
    logger: logging.Logger | None = None,
) -> StatisticsDocument:
    """Read metadata JSON and calculate all requested aggregate statistics.

    Problem numbers are deduplicated before aggregation.  This means a repeated
    LeetHub folder cannot inflate the total solved count or distributions.

    Args:
        metadata_path: Path to the metadata JSON document.
        recent_limit: Maximum number of entries in ``recently_solved``.
        logger: Optional logger for duplicate and malformed-date warnings.

    Returns:
        A serializable statistics document.

    Raises:
        ValueError: If *recent_limit* is negative or metadata is malformed.
        OSError: If *metadata_path* cannot be read.
        json.JSONDecodeError: If *metadata_path* is not valid JSON.
    """

    if recent_limit < 0:
        raise ValueError("recent_limit must not be negative.")

    active_logger = logger or get_logger(__name__)
    problems = _read_metadata_problems(metadata_path)
    unique_problems = _deduplicate_problems(problems, active_logger)
    return _calculate_statistics(unique_problems, recent_limit=recent_limit, logger=active_logger)


def write_statistics(document: StatisticsDocument, output_path: Path) -> None:
    """Atomically write a statistics document as deterministic JSON."""

    write_json_safely(output_path, document.to_dict())


def _read_metadata_problems(metadata_path: Path) -> tuple[MetadataProblem, ...]:
    """Load and validate problem records from a metadata JSON document."""

    document = read_json(metadata_path)
    if not isinstance(document, dict):
        raise ValueError("Metadata JSON must contain an object at its root.")
    records = document.get("problems")
    if not isinstance(records, list):
        raise ValueError("Metadata JSON field 'problems' must be a list.")

    return tuple(_parse_metadata_problem(record, index) for index, record in enumerate(records))


def _parse_metadata_problem(record: Any, index: int) -> MetadataProblem:
    """Validate and normalize one problem record from metadata JSON."""

    if not isinstance(record, dict):
        raise ValueError(f"Metadata problem at index {index} must be an object.")

    number = record.get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number < 0:
        raise ValueError(f"Metadata problem at index {index} has an invalid number.")

    return MetadataProblem(
        number=number,
        name=_required_string(record, "name", index),
        difficulty=_optional_difficulty(record.get("difficulty"), index),
        topics=_string_sequence(record.get("topics"), "topics", index),
        languages=_string_sequence(record.get("languages"), "languages", index),
        folder=_required_string(record, "folder", index),
        leetcode_link=_optional_string(record.get("leetcode_link"), "leetcode_link", index),
        last_modified=_required_string(record, "last_modified", index),
    )


def _required_string(record: Mapping[str, Any], field: str, index: int) -> str:
    """Return a required non-empty string field from a metadata record."""

    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Metadata problem at index {index} has an invalid '{field}'.")
    return value


def _optional_string(value: Any, field: str, index: int) -> str | None:
    """Return an optional string field, rejecting other JSON types."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Metadata problem at index {index} has an invalid '{field}'.")
    return value or None


def _optional_difficulty(value: Any, index: int) -> str | None:
    """Normalize a supported difficulty name or return ``None``."""

    normalized = _optional_string(value, "difficulty", index)
    if normalized is None:
        return None
    candidate = normalized.capitalize()
    if candidate not in _DIFFICULTIES:
        raise ValueError(f"Metadata problem at index {index} has an invalid difficulty.")
    return candidate


def _string_sequence(value: Any, field: str, index: int) -> tuple[str, ...]:
    """Return a normalized, duplicate-free string sequence from metadata."""

    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"Metadata problem at index {index} has invalid '{field}'.")
    return tuple(sorted(set(value), key=str.casefold))


def _deduplicate_problems(
    problems: Iterable[MetadataProblem], logger: logging.Logger
) -> tuple[MetadataProblem, ...]:
    """Keep the most recently modified entry for every duplicated problem number."""

    selected: dict[int, MetadataProblem] = {}
    for problem in problems:
        existing = selected.get(problem.number)
        if existing is None:
            selected[problem.number] = problem
            continue
        chosen = max((existing, problem), key=_modification_sort_key)
        selected[problem.number] = chosen
        logger.warning(
            "Duplicate metadata for problem %s; using folder %s.",
            problem.number,
            chosen.folder,
        )
    return tuple(sorted(selected.values(), key=lambda problem: problem.number))


def _calculate_statistics(
    problems: tuple[MetadataProblem, ...],
    *,
    recent_limit: int,
    logger: logging.Logger,
) -> StatisticsDocument:
    """Aggregate validated, unique metadata records into a statistics document."""

    difficulty_counts = Counter(problem.difficulty for problem in problems if problem.difficulty)
    language_counts = Counter(
        language for problem in problems for language in problem.languages
    )
    topic_counts = Counter(topic for problem in problems for topic in problem.topics)
    total_solved = len(problems)

    difficulty_distribution = tuple(
        _distribution_entry(difficulty, difficulty_counts[difficulty], total_solved)
        for difficulty in _DIFFICULTIES
    )
    ordered_languages = (*_REQUIRED_LANGUAGES, *sorted(
        set(language_counts).difference(_REQUIRED_LANGUAGES), key=str.casefold
    ))
    language_distribution = tuple(
        _distribution_entry(language, language_counts[language], total_solved)
        for language in ordered_languages
    )
    recently_solved = tuple(
        RecentlySolvedProblem(
            number=problem.number,
            name=problem.name,
            folder=problem.folder,
            last_modified=problem.last_modified,
            leetcode_link=problem.leetcode_link,
        )
        for problem in sorted(problems, key=lambda item: _modification_sort_key(item, logger), reverse=True)[
            :recent_limit
        ]
    )

    return StatisticsDocument(
        generated_at=format_date(datetime.now(timezone.utc), include_time=True),
        total_solved=total_solved,
        easy=difficulty_counts["Easy"],
        medium=difficulty_counts["Medium"],
        hard=difficulty_counts["Hard"],
        python_count=language_counts["Python"],
        cpp_count=language_counts["C++"],
        mysql_count=language_counts["MySQL"],
        topic_counts=MappingProxyType(dict(sorted(topic_counts.items(), key=lambda item: item[0].casefold()))),
        recently_solved=recently_solved,
        language_distribution=language_distribution,
        difficulty_distribution=difficulty_distribution,
    )


def _distribution_entry(name: str, count: int, total: int) -> DistributionEntry:
    """Create a percentage distribution entry, safely handling empty input."""

    percentage = round((count / total) * 100, 2) if total else 0.0
    return DistributionEntry(name=name, count=count, percentage=percentage)


def _modification_sort_key(
    problem: MetadataProblem, logger: logging.Logger | None = None
) -> tuple[datetime, int]:
    """Return a safe descending-sort key based on a metadata timestamp."""

    try:
        parsed = datetime.fromisoformat(problem.last_modified.replace("Z", "+00:00"))
        normalized = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        if logger is not None:
            logger.warning(
                "Invalid last_modified value for problem %s: %r", problem.number, problem.last_modified
            )
        normalized = datetime.min.replace(tzinfo=timezone.utc)
    return normalized, problem.number
