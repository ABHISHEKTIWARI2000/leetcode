"""Typed loading and validation for repository automation configuration.

This module deliberately has no repository-specific defaults.  Every setting is
supplied by the JSON configuration file so the automation can be reused without
editing Python source code.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class ConfigurationError(ValueError):
    """Raised when a configuration document is missing or has invalid data."""


@dataclass(frozen=True, slots=True)
class RepositoryConfiguration:
    """Identifies the local repository and its canonical remote URL.

    Attributes:
        path: Repository path as configured, relative or absolute.
        url: Canonical repository URL.
    """

    path: Path
    url: str


@dataclass(frozen=True, slots=True)
class BadgeConfiguration:
    """Defines how generated README badges should be rendered.

    Attributes:
        enabled: Whether badge rendering is enabled.
        style: Provider-specific badge style.
        color: Provider-specific badge colour.
        label: Text displayed as the badge label.
        message: Text displayed as the badge value.
    """

    enabled: bool
    style: str
    color: str
    label: str
    message: str


@dataclass(frozen=True, slots=True)
class ReadmeConfiguration:
    """Defines automation-owned README output settings.

    Attributes:
        output_directory: Directory where generated README files are written.
        dashboard_filename: Filename of the generated dashboard.
        generated_header: Header inserted into generated documents.
    """

    output_directory: Path
    dashboard_filename: str
    generated_header: str


@dataclass(frozen=True, slots=True)
class GitHubActionConfiguration:
    """Defines settings consumed by the GitHub Actions workflow.

    Attributes:
        enabled: Whether automation runs are enabled.
        workflow_path: Repository-relative workflow file path.
        branch: Branch on which generated output may be committed.
        schedule: Cron expression used for scheduled runs.
        auto_commit: Whether successful generation may create a bot commit.
    """

    enabled: bool
    workflow_path: Path
    branch: str
    schedule: str
    auto_commit: bool


@dataclass(frozen=True, slots=True)
class AutomationConfiguration:
    """Complete immutable configuration for the metadata automation.

    Attributes:
        repository: Repository identity and filesystem location.
        leetcode_username: LeetCode profile username.
        supported_languages: Source extension-to-language mapping.
        excluded_folders: Repository-relative folders omitted from scanning.
        badges: Badge rendering configuration.
        readme: README generation configuration.
        github_actions: GitHub Actions configuration.
    """

    repository: RepositoryConfiguration
    leetcode_username: str
    supported_languages: Mapping[str, str]
    excluded_folders: tuple[Path, ...]
    badges: BadgeConfiguration
    readme: ReadmeConfiguration
    github_actions: GitHubActionConfiguration

    def language_for_extension(self, extension: str) -> str | None:
        """Return the configured language for *extension*, if it is supported."""

        return self.supported_languages.get(extension)


def load_configuration(configuration_path: Path) -> AutomationConfiguration:
    """Load and validate an automation JSON configuration document.

    The expected document contains the following required sections:

    ``repository``, ``leetcode_username``, ``supported_languages``,
    ``excluded_folders``, ``badges``, ``readme``, and ``github_actions``.

    Args:
        configuration_path: Path to the JSON configuration file.

    Returns:
        An immutable, fully validated :class:`AutomationConfiguration`.

    Raises:
        ConfigurationError: If the file cannot be read, is not valid JSON, or
            does not meet the required schema.
    """

    document = _read_json(configuration_path)

    repository = _require_mapping(document, "repository")
    badges = _require_mapping(document, "badges")
    readme = _require_mapping(document, "readme")
    github_actions = _require_mapping(document, "github_actions")

    language_mapping = _require_mapping(document, "supported_languages")
    supported_languages: dict[str, str] = {}
    for extension, language in language_mapping.items():
        if not isinstance(extension, str) or not extension.strip():
            raise ConfigurationError(
                "Each 'supported_languages' extension must be a non-empty string."
            )
        if not isinstance(language, str) or not language.strip():
            raise ConfigurationError(
                "Each 'supported_languages' language must be a non-empty string."
            )
        supported_languages[extension] = language
    if not supported_languages:
        raise ConfigurationError("'supported_languages' must not be empty.")

    excluded_folders = _require_string_list(document, "excluded_folders")

    return AutomationConfiguration(
        repository=RepositoryConfiguration(
            path=Path(_require_string(repository, "path")),
            url=_require_string(repository, "url"),
        ),
        leetcode_username=_require_string(document, "leetcode_username"),
        supported_languages=MappingProxyType(supported_languages),
        excluded_folders=tuple(Path(folder) for folder in excluded_folders),
        badges=BadgeConfiguration(
            enabled=_require_boolean(badges, "enabled"),
            style=_require_string(badges, "style"),
            color=_require_string(badges, "color"),
            label=_require_string(badges, "label"),
            message=_require_string(badges, "message"),
        ),
        readme=ReadmeConfiguration(
            output_directory=Path(_require_string(readme, "output_directory")),
            dashboard_filename=_require_string(readme, "dashboard_filename"),
            generated_header=_require_string(readme, "generated_header"),
        ),
        github_actions=GitHubActionConfiguration(
            enabled=_require_boolean(github_actions, "enabled"),
            workflow_path=Path(_require_string(github_actions, "workflow_path")),
            branch=_require_string(github_actions, "branch"),
            schedule=_require_string(github_actions, "schedule"),
            auto_commit=_require_boolean(github_actions, "auto_commit"),
        ),
    )


def _read_json(configuration_path: Path) -> Mapping[str, Any]:
    """Read a JSON object from *configuration_path*."""

    try:
        with configuration_path.open(encoding="utf-8") as configuration_file:
            document = json.load(configuration_file)
    except OSError as error:
        raise ConfigurationError(
            f"Unable to read configuration file: {configuration_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise ConfigurationError(
            f"Configuration file contains invalid JSON: {configuration_path}"
        ) from error

    if not isinstance(document, dict):
        raise ConfigurationError("The configuration document must be a JSON object.")
    return document


def _require_mapping(document: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    """Return a required object field or raise :class:`ConfigurationError`."""

    value = document.get(field)
    if not isinstance(value, dict):
        raise ConfigurationError(f"'{field}' must be a JSON object.")
    return value


def _require_string(document: Mapping[str, Any], field: str) -> str:
    """Return a required, non-empty string field."""

    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"'{field}' must be a non-empty string.")
    return value


def _require_boolean(document: Mapping[str, Any], field: str) -> bool:
    """Return a required Boolean field."""

    value = document.get(field)
    if not isinstance(value, bool):
        raise ConfigurationError(f"'{field}' must be a Boolean.")
    return value


def _require_string_list(document: Mapping[str, Any], field: str) -> list[str]:
    """Return a required list containing only non-empty strings."""

    value = document.get(field)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ConfigurationError(f"'{field}' must be a list of non-empty strings.")
    return value
