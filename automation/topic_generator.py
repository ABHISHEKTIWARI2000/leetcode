"""Generate professional topic index pages from metadata and statistics JSON."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path
import re
from typing import Any

from .utils import escape_markdown, markdown_table, read_json, write_text_safely


def generate_topic_pages(
    metadata_path: Path,
    statistics_path: Path,
    output_directory: Path,
    *,
    descriptions: Mapping[str, str] | None = None,
    filename_overrides: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    """Generate one Markdown page per topic and return the written paths.

    ``descriptions`` and ``filename_overrides`` let repository configuration
    control editorial content and names such as ``dp.md`` without code changes.
    """

    metadata = _object(read_json(metadata_path), "metadata")
    statistics = _object(read_json(statistics_path), "statistics")
    problems = _problems(metadata)
    total_solved = _count(statistics, "total_solved")
    topic_names = sorted(
        {topic for problem in problems for topic in _strings(problem, "topics")},
        key=str.casefold,
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for topic in topic_names:
        matching = [problem for problem in problems if topic in _strings(problem, "topics")]
        filename = (filename_overrides or {}).get(topic, f"{_slugify(topic)}.md")
        destination = output_directory / filename
        description = (descriptions or {}).get(
            topic, f"A curated index of solved problems tagged **{escape_markdown(topic)}**."
        )
        write_text_safely(destination, _render_topic(topic, description, matching, total_solved))
        written.append(destination)
    return tuple(written)


def _render_topic(topic: str, description: str, problems: list[Mapping[str, Any]], total: int) -> str:
    """Render one standalone topic page."""

    difficulties = Counter(_optional_string(problem.get("difficulty")) for problem in problems)
    percentage = round((len(problems) / total) * 100, 2) if total else 0.0
    table = markdown_table(
        ("#", "Problem", "Difficulty", "Languages", "GitHub", "LeetCode", "Last Updated"),
        (
            (
                problem["number"],
                problem["name"],
                problem.get("difficulty") or "—",
                ", ".join(_strings(problem, "languages")) or "—",
                f"[Source]({problem['github_link']})",
                f"[Problem]({problem['leetcode_link']})" if problem.get("leetcode_link") else "—",
                problem["last_modified"],
            )
            for problem in sorted(problems, key=lambda item: int(item["number"]))
        ),
    )
    difficulty_table = markdown_table(
        ("Difficulty", "Solved"),
        ((difficulty, difficulties[difficulty]) for difficulty in ("Easy", "Medium", "Hard")),
    )
    return (
        f"# {escape_markdown(topic)}\n\n"
        f"> {description}\n\n"
        "## Statistics\n\n"
        f"- **Solved in this topic:** {len(problems)}\n"
        f"- **Repository coverage:** {percentage}% of {total} solved problems\n\n"
        "## Difficulty Distribution\n\n"
        f"{difficulty_table}\n\n"
        "## Problem Table\n\n"
        f"{table}\n\n"
        "## Links\n\n"
        "- [Repository dashboard](README.md)\n"
        "- [All topics](solutions-by-topic.md)\n"
    )


def _problems(metadata: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Validate the minimal metadata fields needed by page rendering."""

    raw = metadata.get("problems")
    if not isinstance(raw, list):
        raise ValueError("Metadata field 'problems' must be a list.")
    parsed: list[Mapping[str, Any]] = []
    for index, value in enumerate(raw):
        problem = _object(value, f"problem at index {index}")
        if not isinstance(problem.get("number"), int) or not isinstance(problem.get("name"), str):
            raise ValueError(f"Problem at index {index} has invalid identity fields.")
        for field in ("github_link", "last_modified"):
            if not isinstance(problem.get(field), str):
                raise ValueError(f"Problem at index {index} has invalid '{field}'.")
        _strings(problem, "topics")
        _strings(problem, "languages")
        parsed.append(problem)
    return parsed


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _count(document: Mapping[str, Any], field: str) -> int:
    value = document.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Statistics field '{field}' must be a non-negative integer.")
    return value


def _strings(document: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = document.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"Field '{field}' must be a list of strings.")
    return tuple(value)


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _slugify(value: str) -> str:
    """Create a portable filename stem from a topic name."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValueError("Topic names must contain at least one alphanumeric character.")
    return slug
