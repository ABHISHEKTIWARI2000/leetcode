"""Read-only discovery of solved LeetCode problems in a repository.

The scanner recognizes LeetHub-style directory names such as
``0002-add-two-numbers``.  It never changes repository files and leaves
metadata and README generation to their dedicated modules.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from html import unescape
import logging
from pathlib import Path
import re
from types import MappingProxyType

from .utils import detect_language, get_logger, iter_directories, iter_files, read_text


SUPPORTED_LANGUAGE_EXTENSIONS: Mapping[str, str] = MappingProxyType(
    {
        ".py": "Python",
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".sql": "MySQL",
    }
)
"""Built-in extensions supported by the repository scanner."""

DEFAULT_EXCLUDED_FOLDERS: tuple[Path, ...] = (Path(".git"),)
"""Repository control folders that should never be traversed."""

_PROBLEM_DIRECTORY_PATTERN = re.compile(r"^(?P<number>\d+)[-_](?P<slug>.+)$")
_LEETCODE_URL_PATTERN = re.compile(
    r"https?://leetcode\.com/problems/[^\s\"'<>)]*",
    flags=re.IGNORECASE,
)
_README_TITLE_PATTERN = re.compile(
    r"<a\b[^>]*\bhref\s*=\s*[\"']https?://leetcode\.com/problems/[^\"']+[\"'][^>]*>"
    r"\s*(?:\d+\.\s*)?(?P<title>.*?)\s*</a>",
    flags=re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass(frozen=True, slots=True)
class SolutionFile:
    """A supported solution file discovered under a problem directory.

    Attributes:
        path: Path relative to the repository root.
        language: Configured language identified from the file extension.
    """

    path: Path
    language: str


@dataclass(frozen=True, slots=True)
class SolvedProblem:
    """A solved problem represented by a LeetHub-style directory.

    Attributes:
        number: Numeric LeetCode problem identifier.
        name: Human-readable problem title.
        slug: URL-friendly problem name derived from its directory.
        folder: Problem directory relative to the repository root.
        languages: Distinct detected solution languages, sorted by name.
        solution_files: Supported solution files, sorted by relative path.
        leetcode_url: Canonical problem URL when available in the README.
    """

    number: int
    name: str
    slug: str
    folder: Path
    languages: tuple[str, ...]
    solution_files: tuple[SolutionFile, ...]
    leetcode_url: str | None


@dataclass(frozen=True, slots=True)
class RepositoryScan:
    """The immutable result of scanning one repository.

    ``problems`` contains every detected solved-problem directory, including
    duplicate problem numbers.  ``duplicate_problems`` groups those conflicts
    so callers can report or resolve them without losing source information.
    """

    repository_path: Path
    problems: tuple[SolvedProblem, ...]
    duplicate_problems: Mapping[int, tuple[SolvedProblem, ...]]


def scan_repository(
    repository_path: Path,
    *,
    excluded_folders: Iterable[Path] = DEFAULT_EXCLUDED_FOLDERS,
    language_extensions: Mapping[str, str] = SUPPORTED_LANGUAGE_EXTENSIONS,
    logger: logging.Logger | None = None,
) -> RepositoryScan:
    """Recursively discover solved problems in *repository_path*.

    A directory is considered a solved problem only when its name contains a
    numeric prefix and it contains at least one supported Python, C++, or MySQL
    solution file.  The function is read-only and does not generate outputs.

    Args:
        repository_path: Root directory of the repository to scan.
        excluded_folders: Directories, relative to the root or absolute, to skip.
        language_extensions: Extension-to-language mapping used for detection.
        logger: Optional logger for scan progress and duplicate warnings.

    Returns:
        Structured records for all solved problems and their duplicate numbers.

    Raises:
        NotADirectoryError: If *repository_path* is not an existing directory.
    """

    active_logger = logger or get_logger(__name__)
    root = repository_path.resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    candidate_directories = _find_problem_directories(root, excluded_folders)
    active_logger.info("Found %d candidate problem directories.", len(candidate_directories))

    candidate_paths = {directory.resolve() for directory in candidate_directories}
    problems: list[SolvedProblem] = []
    for directory in candidate_directories:
        problem = _scan_problem_directory(root, directory, candidate_paths, language_extensions)
        if problem is None:
            active_logger.debug("Skipped candidate without a supported solution: %s", directory)
            continue
        problems.append(problem)

    ordered_problems = tuple(sorted(problems, key=lambda item: (item.number, item.folder.as_posix())))
    duplicates = _find_duplicates(ordered_problems)
    for number, duplicate_entries in duplicates.items():
        active_logger.warning(
            "Detected duplicate problem %s in: %s",
            number,
            ", ".join(entry.folder.as_posix() for entry in duplicate_entries),
        )

    active_logger.info("Detected %d solved problems.", len(ordered_problems))
    return RepositoryScan(
        repository_path=root,
        problems=ordered_problems,
        duplicate_problems=MappingProxyType(duplicates),
    )


def _find_problem_directories(root: Path, excluded_folders: Iterable[Path]) -> tuple[Path, ...]:
    """Return sorted directories whose names match the LeetHub convention."""

    candidates = [
        directory
        for directory in iter_directories(root, excluded_directories=excluded_folders)
        if _PROBLEM_DIRECTORY_PATTERN.fullmatch(directory.name)
    ]
    return tuple(sorted(candidates, key=lambda item: item.as_posix()))


def _scan_problem_directory(
    root: Path,
    directory: Path,
    all_candidate_paths: set[Path],
    language_extensions: Mapping[str, str],
) -> SolvedProblem | None:
    """Build a record for one candidate directory, or return ``None``."""

    match = _PROBLEM_DIRECTORY_PATTERN.fullmatch(directory.name)
    if match is None:
        return None

    nested_candidates = [
        candidate.relative_to(directory)
        for candidate in all_candidate_paths
        if candidate != directory.resolve() and _is_relative_to(candidate, directory.resolve())
    ]
    solution_files = tuple(
        SolutionFile(path=file_path.relative_to(root), language=language)
        for file_path in iter_files(directory, excluded_directories=nested_candidates)
        if (language := detect_language(file_path, language_extensions)) is not None
    )
    if not solution_files:
        return None

    readme_path = directory / "README.md"
    leetcode_url, readme_name = _readme_details(readme_path)
    slug = match.group("slug")
    return SolvedProblem(
        number=int(match.group("number")),
        name=readme_name or _name_from_slug(slug),
        slug=slug,
        folder=directory.relative_to(root),
        languages=tuple(sorted({entry.language for entry in solution_files})),
        solution_files=tuple(sorted(solution_files, key=lambda item: item.path.as_posix())),
        leetcode_url=leetcode_url,
    )


def _readme_details(readme_path: Path) -> tuple[str | None, str | None]:
    """Extract a canonical URL and displayed title from a problem README."""

    if not readme_path.is_file():
        return None, None

    try:
        content = read_text(readme_path)
    except OSError:
        return None, None

    url_match = _LEETCODE_URL_PATTERN.search(content)
    title_match = _README_TITLE_PATTERN.search(content)
    title = None
    if title_match is not None:
        title = unescape(_HTML_TAG_PATTERN.sub("", title_match.group("title"))).strip()
    return (url_match.group(0) if url_match is not None else None), title or None


def _name_from_slug(slug: str) -> str:
    """Convert a directory slug into a readable fallback title."""

    return " ".join(part.capitalize() for part in re.split(r"[-_]+", slug) if part)


def _find_duplicates(
    problems: tuple[SolvedProblem, ...],
) -> dict[int, tuple[SolvedProblem, ...]]:
    """Group only problem numbers with more than one discovered directory."""

    grouped: defaultdict[int, list[SolvedProblem]] = defaultdict(list)
    for problem in problems:
        grouped[problem.number].append(problem)
    return {
        number: tuple(entries)
        for number, entries in grouped.items()
        if len(entries) > 1
    }


def _is_relative_to(candidate: Path, parent: Path) -> bool:
    """Return whether *candidate* is strictly contained by *parent*."""

    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True
