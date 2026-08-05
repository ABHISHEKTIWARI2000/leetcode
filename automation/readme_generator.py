"""Render a repository README from metadata and statistics with Jinja2.

Markdown is intentionally kept outside this module in a caller-supplied Jinja2
template.  This keeps presentation versioned independently from Python logic
and prevents accidental edits to LeetHub-managed README files.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .utils import read_json, write_text_safely


@dataclass(frozen=True, slots=True)
class ProjectDetails:
    """Project-level content made available to the README template."""

    title: str
    banner_url: str
    about: str
    repository_url: str
    leetcode_profile_url: str


@dataclass(frozen=True, slots=True)
class Badge:
    """A presentation-neutral badge that a template can render as a link/image."""

    label: str
    image_url: str
    target_url: str


@dataclass(frozen=True, slots=True)
class RepositoryStructureEntry:
    """One repository path and its purpose for the structure section."""

    path: str
    description: str


@dataclass(frozen=True, slots=True)
class DistributionItem:
    """A named count and percentage used in distribution sections."""

    name: str
    count: int
    percentage: float


@dataclass(frozen=True, slots=True)
class RecentProblem:
    """A compact record for the recently solved section."""

    number: int
    name: str
    folder: str
    last_modified: str
    leetcode_link: str | None


@dataclass(frozen=True, slots=True)
class ProblemTableRow:
    """One searchable-problem-table row, ready for Jinja2 rendering."""

    number: int
    name: str
    difficulty: str | None
    topics: tuple[str, ...]
    python: bool
    cpp: bool
    mysql: bool
    github_link: str
    leetcode_link: str | None
    last_updated: str


@dataclass(frozen=True, slots=True)
class ReadmeContext:
    """All normalized content required by the external README template."""

    project: ProjectDetails
    badges: tuple[Badge, ...]
    total_solved: int
    easy: int
    medium: int
    hard: int
    python_count: int
    cpp_count: int
    mysql_count: int
    topic_counts: Mapping[str, int]
    difficulty_distribution: tuple[DistributionItem, ...]
    language_distribution: tuple[DistributionItem, ...]
    recently_solved: tuple[RecentProblem, ...]
    repository_structure: tuple[RepositoryStructureEntry, ...]
    problem_table: tuple[ProblemTableRow, ...]

    def to_template_context(self) -> dict[str, object]:
        """Return Jinja2-ready values without embedding presentation markup."""

        return {
            "project": self.project,
            "badges": self.badges,
            "statistics": {
                "total_solved": self.total_solved,
                "easy": self.easy,
                "medium": self.medium,
                "hard": self.hard,
                "python_count": self.python_count,
                "cpp_count": self.cpp_count,
                "mysql_count": self.mysql_count,
                "topic_counts": self.topic_counts,
                "difficulty_distribution": self.difficulty_distribution,
                "language_distribution": self.language_distribution,
            },
            "recently_solved": self.recently_solved,
            "repository_structure": self.repository_structure,
            "problem_table": self.problem_table,
        }


def build_readme_context(
    metadata_path: Path,
    statistics_path: Path,
    *,
    project: ProjectDetails,
    badges: Sequence[Badge],
    repository_structure: Sequence[RepositoryStructureEntry],
) -> ReadmeContext:
    """Load generated JSON and construct a validated README template context.

    Args:
        metadata_path: Path to the JSON emitted by the metadata builder.
        statistics_path: Path to the JSON emitted by the statistics generator.
        project: Banner, about text, and project links for the template.
        badges: Badge definitions for the badge section.
        repository_structure: Entries for the repository-structure section.

    Returns:
        A complete, typed context for a professional Jinja2 README template.

    Raises:
        ValueError: If either input JSON document has an invalid shape.
    """

    metadata = _require_object(read_json(metadata_path), "metadata")
    statistics = _require_object(read_json(statistics_path), "statistics")
    problem_table = _parse_problem_table(metadata)

    return ReadmeContext(
        project=project,
        badges=tuple(badges),
        total_solved=_required_non_negative_int(statistics, "total_solved"),
        easy=_required_non_negative_int(statistics, "easy"),
        medium=_required_non_negative_int(statistics, "medium"),
        hard=_required_non_negative_int(statistics, "hard"),
        python_count=_required_non_negative_int(statistics, "python_count"),
        cpp_count=_required_non_negative_int(statistics, "cpp_count"),
        mysql_count=_required_non_negative_int(statistics, "mysql_count"),
        topic_counts=_parse_topic_counts(statistics),
        difficulty_distribution=_parse_distribution(
            statistics, "difficulty_distribution", "difficulty"
        ),
        language_distribution=_parse_distribution(
            statistics, "language_distribution", "language"
        ),
        recently_solved=_parse_recent_problems(statistics),
        repository_structure=tuple(repository_structure),
        problem_table=problem_table,
    )


def render_readme(
    context: ReadmeContext,
    *,
    template_path: Path,
    output_path: Path,
) -> None:
    """Render an external Jinja2 template and safely publish its Markdown.

    The template receives ``context.to_template_context()``.  It is expected to
    render the project banner, about section, badges, statistics, structure,
    recent problems, and searchable problem table from those values.

    Args:
        context: Normalized README data.
        template_path: Filesystem path to the Jinja2 Markdown template.
        output_path: Explicit destination for the rendered README.

    Raises:
        RuntimeError: If Jinja2 is unavailable or the template cannot be found.
    """

    try:
        from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
    except ImportError as error:
        raise RuntimeError(
            "Jinja2 is required to render README templates. Install the project dependencies."
        ) from error

    if not template_path.is_file():
        raise RuntimeError(f"README template does not exist: {template_path}")

    environment = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    try:
        template = environment.get_template(template_path.name)
    except TemplateNotFound as error:
        raise RuntimeError(f"Unable to load README template: {template_path}") from error

    rendered = template.render(**context.to_template_context()).rstrip() + "\n"
    write_text_safely(output_path, rendered)


def _parse_problem_table(metadata: Mapping[str, Any]) -> tuple[ProblemTableRow, ...]:
    """Validate metadata records and convert them into table rows."""

    problems = metadata.get("problems")
    if not isinstance(problems, list):
        raise ValueError("Metadata field 'problems' must be a list.")

    rows = [_parse_problem_row(problem, index) for index, problem in enumerate(problems)]
    return tuple(sorted(rows, key=lambda row: (row.number, row.name.casefold())))


def _parse_problem_row(record: Any, index: int) -> ProblemTableRow:
    """Create a validated table row from one metadata problem record."""

    problem = _require_object(record, f"metadata problem at index {index}")
    languages = _string_list(problem, "languages", index)
    return ProblemTableRow(
        number=_required_non_negative_int(problem, "number"),
        name=_required_string(problem, "name", index),
        difficulty=_optional_string(problem.get("difficulty"), "difficulty", index),
        topics=_string_list(problem, "topics", index),
        python="Python" in languages,
        cpp="C++" in languages,
        mysql="MySQL" in languages,
        github_link=_required_string(problem, "github_link", index),
        leetcode_link=_optional_string(problem.get("leetcode_link"), "leetcode_link", index),
        last_updated=_required_string(problem, "last_modified", index),
    )


def _parse_topic_counts(statistics: Mapping[str, Any]) -> Mapping[str, int]:
    """Validate and return topic counts in deterministic alphabetical order."""

    raw_counts = _require_object(statistics.get("topic_counts"), "topic_counts")
    parsed: dict[str, int] = {}
    for topic, count in raw_counts.items():
        if not isinstance(topic, str) or not topic.strip() or not _is_non_negative_int(count):
            raise ValueError("Statistics field 'topic_counts' contains an invalid entry.")
        parsed[topic] = count
    return MappingProxyType(dict(sorted(parsed.items(), key=lambda item: item[0].casefold())))


def _parse_distribution(
    statistics: Mapping[str, Any], field: str, name_field: str
) -> tuple[DistributionItem, ...]:
    """Validate one language or difficulty distribution array."""

    values = statistics.get(field)
    if not isinstance(values, list):
        raise ValueError(f"Statistics field '{field}' must be a list.")

    parsed: list[DistributionItem] = []
    for index, value in enumerate(values):
        entry = _require_object(value, f"{field} entry at index {index}")
        name = _required_string(entry, name_field, index)
        count = _required_non_negative_int(entry, "count")
        percentage = entry.get("percentage")
        if not isinstance(percentage, (int, float)) or isinstance(percentage, bool):
            raise ValueError(f"{field} entry at index {index} has an invalid percentage.")
        parsed.append(DistributionItem(name=name, count=count, percentage=float(percentage)))
    return tuple(parsed)


def _parse_recent_problems(statistics: Mapping[str, Any]) -> tuple[RecentProblem, ...]:
    """Validate recently solved records supplied by the statistics generator."""

    values = statistics.get("recently_solved")
    if not isinstance(values, list):
        raise ValueError("Statistics field 'recently_solved' must be a list.")

    parsed: list[RecentProblem] = []
    for index, value in enumerate(values):
        entry = _require_object(value, f"recently_solved entry at index {index}")
        parsed.append(
            RecentProblem(
                number=_required_non_negative_int(entry, "number"),
                name=_required_string(entry, "name", index),
                folder=_required_string(entry, "folder", index),
                last_modified=_required_string(entry, "last_modified", index),
                leetcode_link=_optional_string(entry.get("leetcode_link"), "leetcode_link", index),
            )
        )
    return tuple(parsed)


def _require_object(value: Any, label: str) -> Mapping[str, Any]:
    """Return a JSON object or raise a useful validation error."""

    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _required_non_negative_int(document: Mapping[str, Any], field: str) -> int:
    """Read a required non-negative integer from a JSON object."""

    value = document.get(field)
    if not _is_non_negative_int(value):
        raise ValueError(f"Field '{field}' must be a non-negative integer.")
    return value


def _is_non_negative_int(value: Any) -> bool:
    """Return whether *value* is an integer count but not a Boolean."""

    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _required_string(document: Mapping[str, Any], field: str, index: int) -> str:
    """Read a required non-empty string from a JSON object."""

    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Entry at index {index} has an invalid '{field}'.")
    return value


def _optional_string(value: Any, field: str, index: int) -> str | None:
    """Read a nullable string from a JSON object."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Entry at index {index} has an invalid '{field}'.")
    return value or None


def _string_list(document: Mapping[str, Any], field: str, index: int) -> tuple[str, ...]:
    """Read a duplicate-free list of non-empty strings from a JSON object."""

    value = document.get(field)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"Entry at index {index} has an invalid '{field}'.")
    return tuple(sorted(set(value), key=str.casefold))
