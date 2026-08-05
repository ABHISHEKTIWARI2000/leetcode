"""Command-line orchestrator for the LeetCode repository automation pipeline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from automation.config import AutomationConfiguration, ConfigurationError, load_configuration
from automation.difficulty_generator import generate_difficulty_pages
from automation.metadata_builder import build_metadata, write_metadata
from automation.readme_generator import Badge, ProjectDetails, RepositoryStructureEntry, build_readme_context, render_readme
from automation.repository_scanner import scan_repository
from automation.stats_generator import generate_statistics, write_statistics
from automation.topic_generator import generate_topic_pages
from automation.utils import get_logger


@dataclass(frozen=True, slots=True)
class PipelinePaths:
    """Explicit, automation-owned input and output locations for a pipeline run."""

    metadata: Path
    statistics: Path
    documentation: Path
    readme_template: Path


def run_pipeline(configuration: AutomationConfiguration, paths: PipelinePaths) -> None:
    """Run scanning and generation without writing to LeetHub-managed paths."""

    logger = get_logger(__name__)
    logger.info("Scanning repository: %s", configuration.repository.path)
    scan = scan_repository(
        configuration.repository.path,
        excluded_folders=configuration.excluded_folders,
        language_extensions=configuration.supported_languages,
        logger=logger,
    )
    logger.info("Building metadata for %d detected problems.", len(scan.problems))
    metadata = build_metadata(
        scan,
        repository_url=configuration.repository.url,
        branch=configuration.github_actions.branch,
        logger=logger,
    )
    write_metadata(metadata, paths.metadata)

    logger.info("Generating statistics.")
    statistics = generate_statistics(paths.metadata, logger=logger)
    write_statistics(statistics, paths.statistics)

    logger.info("Generating README and index pages.")
    context = build_readme_context(
        paths.metadata,
        paths.statistics,
        project=_project_details(configuration),
        badges=(_badge(configuration),) if configuration.badges.enabled else (),
        repository_structure=_repository_structure(configuration),
    )
    render_readme(
        context,
        template_path=paths.readme_template,
        output_path=paths.documentation / configuration.readme.dashboard_filename,
    )
    generate_topic_pages(paths.metadata, paths.statistics, paths.documentation / "topics")
    generate_difficulty_pages(paths.metadata, paths.statistics, paths.documentation / "difficulties")
    logger.info("Automation pipeline completed successfully.")


def _project_details(configuration: AutomationConfiguration) -> ProjectDetails:
    """Adapt configured repository settings to the README renderer contract."""

    return ProjectDetails(
        title=configuration.repository.url.rstrip("/").rsplit("/", 1)[-1],
        banner_url="",
        about=configuration.readme.generated_header,
        repository_url=configuration.repository.url,
        leetcode_profile_url=f"https://leetcode.com/u/{quote(configuration.leetcode_username, safe='')}/",
    )


def _badge(configuration: AutomationConfiguration) -> Badge:
    """Create a Shields.io-compatible badge from declarative badge settings."""

    settings = configuration.badges
    image_url = (
        "https://img.shields.io/badge/"
        f"{quote(settings.label, safe='')}-{quote(settings.message, safe='')}-"
        f"{quote(settings.color, safe='')}?style={quote(settings.style, safe='')}"
    )
    return Badge(settings.label, image_url, configuration.repository.url)


def _repository_structure(configuration: AutomationConfiguration) -> tuple[RepositoryStructureEntry, ...]:
    """Expose automation-owned output areas in the rendered structure section."""

    return (
        RepositoryStructureEntry("data/", "Generated metadata and statistics"),
        RepositoryStructureEntry(
            str(configuration.readme.output_directory),
            "Generated repository documentation and indexes",
        ),
    )


def _parse_arguments() -> argparse.Namespace:
    """Parse command-line paths while retaining safe automation-owned defaults."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/automation.json"))
    parser.add_argument("--metadata", type=Path, default=Path("data/metadata.json"))
    parser.add_argument("--statistics", type=Path, default=Path("data/statistics.json"))
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    parser.add_argument("--readme-template", type=Path, default=Path("templates/repository-readme.md.j2"))
    return parser.parse_args()


def main() -> int:
    """Execute the pipeline and return a process-compatible exit code."""

    arguments = _parse_arguments()
    logger = get_logger(__name__)
    try:
        configuration = load_configuration(arguments.config)
        run_pipeline(
            configuration,
            PipelinePaths(arguments.metadata, arguments.statistics, arguments.docs, arguments.readme_template),
        )
    except (ConfigurationError, OSError, RuntimeError, ValueError) as error:
        logger.exception("Automation pipeline failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
