"""Reusable, side-effect-aware utilities for repository automation.

The functions in this module are intentionally domain-neutral.  Repository
scanning and LeetCode-specific interpretation belong in dedicated modules.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from datetime import date, datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger without adding duplicate handlers.

    Args:
        name: Logger name, normally the calling module's ``__name__``.
        level: Logging level assigned to the returned logger.

    Returns:
        A logger that writes timestamped messages to standard error.
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        logger.addHandler(handler)

    return logger


def read_text(path: Path, *, encoding: str = "utf-8") -> str:
    """Read and return text from *path* using the requested encoding."""

    return path.read_text(encoding=encoding)


def read_json(path: Path, *, encoding: str = "utf-8") -> JsonValue:
    """Read a JSON document from *path*.

    JSON parsing errors and filesystem errors are intentionally propagated to
    the caller, which has the context to decide whether they are recoverable.
    """

    return json.loads(read_text(path, encoding=encoding))


def write_text_safely(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Atomically write text to *path*, creating parent directories as needed.

    The temporary file is created in the destination directory so
    :meth:`Path.replace` remains an atomic operation on a single filesystem.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_json_safely(
    path: Path,
    document: JsonValue,
    *,
    indent: int = 2,
    encoding: str = "utf-8",
) -> None:
    """Serialize *document* as deterministic JSON and atomically write it."""

    content = json.dumps(
        document,
        ensure_ascii=False,
        indent=indent,
        sort_keys=True,
    )
    write_text_safely(path, f"{content}\n", encoding=encoding)


def iter_files(root: Path, *, excluded_directories: Iterable[Path] = ()) -> Iterator[Path]:
    """Yield files below *root*, excluding the supplied directory paths.

    Exclusions are interpreted relative to *root* unless they are absolute.
    Results are yielded in deterministic, path-sorted order.
    """

    resolved_root = root.resolve()
    exclusions = {
        (entry if entry.is_absolute() else resolved_root / entry).resolve()
        for entry in excluded_directories
    }

    for current_directory, directory_names, filenames in _walk_directories(
        resolved_root, exclusions
    ):
        for filename in filenames:
            yield current_directory / filename


def iter_directories(
    root: Path, *, excluded_directories: Iterable[Path] = ()
) -> Iterator[Path]:
    """Yield child directories below *root* in deterministic order.

    The root directory itself is not yielded.
    """

    resolved_root = root.resolve()
    exclusions = {
        (entry if entry.is_absolute() else resolved_root / entry).resolve()
        for entry in excluded_directories
    }

    for current_directory, directory_names, _ in _walk_directories(
        resolved_root, exclusions
    ):
        for directory_name in directory_names:
            yield current_directory / directory_name


def _walk_directories(
    root: Path, exclusions: set[Path]
) -> Iterator[tuple[Path, list[str], list[str]]]:
    """Yield deterministic directory-walk entries without following symlinks."""

    if not root.is_dir():
        raise NotADirectoryError(root)

    pending = [root]
    while pending:
        current_directory = pending.pop()
        directories: list[str] = []
        files: list[str] = []

        for child in sorted(current_directory.iterdir(), key=lambda entry: entry.name.casefold()):
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.resolve() not in exclusions:
                    directories.append(child.name)
            elif child.is_file():
                files.append(child.name)

        pending.extend(
            current_directory / directory_name
            for directory_name in reversed(directories)
        )
        yield current_directory, directories, files


def format_date(value: date | datetime, *, include_time: bool = False) -> str:
    """Format a date or datetime using a stable ISO-8601 representation.

    Naive datetimes are treated as UTC.  Aware datetimes are normalized to UTC.
    """

    if isinstance(value, datetime):
        normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return normalized.strftime("%Y-%m-%dT%H:%M:%SZ") if include_time else normalized.date().isoformat()
    return value.isoformat()


def detect_language(path: Path, extension_mapping: Mapping[str, str]) -> str | None:
    """Return the configured language for *path* based on its suffix.

    The mapping is caller-provided so language policy remains configuration-led.
    """

    return extension_mapping.get(path.suffix.lower())


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the hexadecimal SHA-256 digest of a file.

    Args:
        path: File to hash.
        chunk_size: Number of bytes read per iteration; must be positive.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        while chunk := source_file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def escape_markdown(value: str) -> str:
    """Escape table-sensitive Markdown characters in plain text."""

    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def markdown_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """Build a GitHub-Flavored Markdown table from headers and row values.

    Raises:
        ValueError: If there are no headers or a row has a mismatched width.
    """

    if not headers:
        raise ValueError("A Markdown table requires at least one header.")

    escaped_headers = [escape_markdown(header) for header in headers]
    lines = [
        f"| {' | '.join(escaped_headers)} |",
        f"| {' | '.join('---' for _ in headers)} |",
    ]
    for row in rows:
        if len(row) != len(headers):
            raise ValueError("Each Markdown table row must match the header width.")
        lines.append(f"| {' | '.join(escape_markdown(str(cell)) for cell in row)} |")
    return "\n".join(lines)
