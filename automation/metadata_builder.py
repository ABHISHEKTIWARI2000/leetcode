"""Build clean problem metadata JSON from repository scan results.

This module only reads repository content and writes the requested metadata
document when :func:`write_metadata` is explicitly called.  It does not render
README files or calculate aggregate statistics.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import logging
import re
from types import MappingProxyType
from urllib.parse import quote

from .repository_scanner import RepositoryScan, SolvedProblem
from .utils import format_date, get_logger, read_text, write_json_safely


_DIFFICULTY_PATTERN = re.compile(
    r"<h3[^>]*>\s*(?P<difficulty>easy|medium|hard)\s*</h3>",
    flags=re.IGNORECASE,
)
_TOPIC_HEADING_PATTERN = re.compile(r"^##\s+(?P<topic>.+?)\s*$", re.MULTILINE)
_PROBLEM_LINK_PATTERN = re.compile(r"\[(?P<folder>\d+[-_][^\]]+)\]\(")


@dataclass(frozen=True, slots=True)
class ProblemMetadata:
    """Serializable metadata for one solved problem.

    Attributes:
        number: Numeric LeetCode problem identifier.
        name: Human-readable problem title.
        difficulty: LeetCode difficulty when available from the problem README.
        topics: Topics extracted from the LeetHub-managed root README.
        languages: Detected implementation languages.
        folder: Repository-relative LeetHub problem folder.
        github_link: Direct link to the folder in the configured GitHub branch.
        leetcode_link: Canonical LeetCode URL when available.
        last_modified: Latest source-file modification time in UTC ISO-8601 form.
    """

    number: int
    name: str
    difficulty: str | None
    topics: tuple[str, ...]
    languages: tuple[str, ...]
    folder: str
    github_link: str
    leetcode_link: str | None
    last_modified: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation with stable field names."""

        return {
            "number": self.number,
            "name": self.name,
            "difficulty": self.difficulty,
            "topics": list(self.topics),
            "languages": list(self.languages),
            "folder": self.folder,
            "github_link": self.github_link,
            "leetcode_link": self.leetcode_link,
            "last_modified": self.last_modified,
        }


@dataclass(frozen=True, slots=True)
class MetadataDocument:
    """The complete serializable metadata output.

    Attributes:
        generated_at: UTC ISO-8601 time at which the document was built.
        problems: Metadata records sorted by problem number and folder.
    """

    generated_at: str
    problems: tuple[ProblemMetadata, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a clean JSON-compatible metadata document."""

        return {
            "generated_at": self.generated_at,
            "problems": [problem.to_dict() for problem in self.problems],
        }


def build_metadata(
    scan: RepositoryScan,
    *,
    repository_url: str,
    branch: str,
    logger: logging.Logger | None = None,
) -> MetadataDocument:
    """Build metadata from a completed repository scan.

    Difficulty is read from each LeetHub-generated problem README.  Topics are
    read from the LeetHub-managed root README.  Missing source values remain
    explicit as ``null`` or empty arrays in the resulting JSON.

    Args:
        scan: Immutable result returned by :func:`scan_repository`.
        repository_url: Canonical GitHub repository URL.
        branch: Git branch used to form folder links.
        logger: Optional logger used for non-fatal enrichment warnings.

    Returns:
        A deterministic, JSON-serializable metadata document.

    Raises:
        ValueError: If *repository_url* or *branch* is empty.
    """

    if not repository_url.strip():
        raise ValueError("repository_url must not be empty.")
    if not branch.strip():
        raise ValueError("branch must not be empty.")

    active_logger = logger or get_logger(__name__)
    topics_by_folder = _read_topics(scan.repository_path, active_logger)
    repository_base_url = repository_url.rstrip("/")
    problems = tuple(
        _build_problem_metadata(
            problem,
            repository_path=scan.repository_path,
            repository_base_url=repository_base_url,
            branch=branch,
            topics=topics_by_folder.get(problem.folder.as_posix(), ()),
            logger=active_logger,
        )
        for problem in scan.problems
    )
    return MetadataDocument(
        generated_at=format_date(datetime.now(timezone.utc), include_time=True),
        problems=problems,
    )


def write_metadata(document: MetadataDocument, output_path: Path) -> None:
    """Write *document* as clean, atomically published JSON at *output_path*."""

    write_json_safely(output_path, document.to_dict())


def _build_problem_metadata(
    problem: SolvedProblem,
    *,
    repository_path: Path,
    repository_base_url: str,
    branch: str,
    topics: Iterable[str],
    logger: logging.Logger,
) -> ProblemMetadata:
    """Enrich one scanned problem into a serializable metadata record."""

    folder = problem.folder.as_posix()
    return ProblemMetadata(
        number=problem.number,
        name=problem.name,
        difficulty=_read_difficulty(repository_path / problem.folder / "README.md", logger),
        topics=tuple(sorted(set(topics), key=str.casefold)),
        languages=problem.languages,
        folder=folder,
        github_link=_github_folder_url(repository_base_url, branch, folder),
        leetcode_link=problem.leetcode_url,
        last_modified=_last_modified(problem, repository_path),
    )


def _read_difficulty(readme_path: Path, logger: logging.Logger) -> str | None:
    """Read a LeetCode difficulty from a problem README, if present."""

    if not readme_path.is_file():
        return None
    try:
        content = read_text(readme_path)
    except OSError as error:
        logger.warning("Could not read problem README %s: %s", readme_path, error)
        return None

    match = _DIFFICULTY_PATTERN.search(content)
    return match.group("difficulty").capitalize() if match is not None else None


def _read_topics(repository_path: Path, logger: logging.Logger) -> Mapping[str, tuple[str, ...]]:
    """Map LeetHub root-README topic headings to linked problem folders."""

    readme_path = repository_path / "README.md"
    if not readme_path.is_file():
        return MappingProxyType({})
    try:
        content = read_text(readme_path)
    except OSError as error:
        logger.warning("Could not read root README %s: %s", readme_path, error)
        return MappingProxyType({})

    topics_by_folder: defaultdict[str, list[str]] = defaultdict(list)
    headings = list(_TOPIC_HEADING_PATTERN.finditer(content))
    for index, heading in enumerate(headings):
        section_end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        topic = heading.group("topic").strip()
        section = content[heading.end() : section_end]
        for folder_match in _PROBLEM_LINK_PATTERN.finditer(section):
            topics_by_folder[folder_match.group("folder")].append(topic)

    return MappingProxyType(
        {
            folder: tuple(sorted(set(topics), key=str.casefold))
            for folder, topics in topics_by_folder.items()
        }
    )


def _github_folder_url(repository_url: str, branch: str, folder: str) -> str:
    """Build an encoded GitHub tree URL for a repository-relative folder."""

    return "/".join(
        (
            repository_url,
            "tree",
            quote(branch, safe=""),
            quote(folder, safe="/"),
        )
    )


def _last_modified(problem: SolvedProblem, repository_path: Path) -> str:
    """Return the latest discovered solution-file timestamp in UTC.

    Scanner records describe files that existed during scanning.  If a file is
    removed before metadata creation, it is skipped; the remaining files still
    provide a stable best-effort timestamp.
    """

    timestamps: list[float] = []
    for solution_file in problem.solution_files:
        try:
            timestamps.append((repository_path / solution_file.path).stat().st_mtime)
        except OSError:
            continue

    if not timestamps:
        return ""
    return format_date(
        datetime.fromtimestamp(max(timestamps), tz=timezone.utc),
        include_time=True,
    )
