"""Generate professional difficulty index pages from metadata and statistics JSON."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .utils import escape_markdown, markdown_table, read_json, write_text_safely


_DIFFICULTIES: tuple[str, ...] = ("Easy", "Medium", "Hard")


def generate_difficulty_pages(
    metadata_path: Path,
    statistics_path: Path,
    output_directory: Path,
    *,
    descriptions: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    """Generate ``easy.md``, ``medium.md``, and ``hard.md`` in *output_directory*."""

    metadata = _object(read_json(metadata_path), "metadata")
    statistics = _object(read_json(statistics_path), "statistics")
    problems = _problems(metadata)
    total_solved = _count(statistics, "total_solved")
    distribution = _distribution(statistics)
    output_directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for difficulty in _DIFFICULTIES:
        matching = [item for item in problems if item.get("difficulty") == difficulty]
        description = (descriptions or {}).get(
            difficulty, f"A focused collection of **{difficulty}** LeetCode solutions."
        )
        destination = output_directory / f"{difficulty.casefold()}.md"
        write_text_safely(
            destination,
            _render_difficulty(difficulty, description, matching, total_solved, distribution),
        )
        written.append(destination)
    return tuple(written)


def _render_difficulty(
    difficulty: str,
    description: str,
    problems: list[Mapping[str, Any]],
    total_solved: int,
    distribution: tuple[tuple[str, int], ...],
) -> str:
    """Render one difficulty page with a compact professional layout."""

    coverage = round((len(problems) / total_solved) * 100, 2) if total_solved else 0.0
    distribution_table = markdown_table(("Difficulty", "Solved"), distribution)
    problem_table = markdown_table(
        ("#", "Problem", "Topics", "Languages", "GitHub", "LeetCode", "Last Updated"),
        (
            (
                item["number"], item["name"], ", ".join(_strings(item, "topics")) or "—",
                ", ".join(_strings(item, "languages")) or "—",
                f"[Source]({item['github_link']})",
                f"[Problem]({item['leetcode_link']})" if item.get("leetcode_link") else "—",
                item["last_modified"],
            )
            for item in sorted(problems, key=lambda value: int(value["number"]))
        ),
    )
    return (
        f"# {escape_markdown(difficulty)} Problems\n\n> {description}\n\n"
        "## Statistics\n\n"
        f"- **Solved at this difficulty:** {len(problems)}\n"
        f"- **Repository coverage:** {coverage}% of {total_solved} solved problems\n\n"
        f"## Difficulty Distribution\n\n{distribution_table}\n\n"
        f"## Problem Table\n\n{problem_table}\n\n"
        "## Links\n\n- [Repository dashboard](README.md)\n- [All difficulties](solutions-by-difficulty.md)\n"
    )


def _problems(metadata: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = metadata.get("problems")
    if not isinstance(raw, list):
        raise ValueError("Metadata field 'problems' must be a list.")
    parsed: list[Mapping[str, Any]] = []
    for index, value in enumerate(raw):
        problem = _object(value, f"problem at index {index}")
        required = ("number", "name", "github_link", "last_modified")
        if not isinstance(problem.get("number"), int) or any(
            not isinstance(problem.get(field), str) for field in required[1:]
        ):
            raise ValueError(f"Problem at index {index} has invalid required fields.")
        _strings(problem, "topics")
        _strings(problem, "languages")
        parsed.append(problem)
    return parsed


def _distribution(statistics: Mapping[str, Any]) -> tuple[tuple[str, int], ...]:
    raw = statistics.get("difficulty_distribution")
    if not isinstance(raw, list):
        raise ValueError("Statistics field 'difficulty_distribution' must be a list.")
    values: dict[str, int] = {}
    for entry in raw:
        item = _object(entry, "difficulty distribution entry")
        name, count = item.get("difficulty"), item.get("count")
        if (
            not isinstance(name, str)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            raise ValueError("Difficulty distribution contains an invalid entry.")
        values[name] = count
    return tuple((difficulty, values.get(difficulty, 0)) for difficulty in _DIFFICULTIES)


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
