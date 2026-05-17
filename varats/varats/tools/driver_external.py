"""
Driver module for `vara-external`.

This module provides a command line interface for setting up and managing
external source repositories that contain custom projects, experiments,
tables, plots, and reports.
"""
import logging
from pathlib import Path

import click

import varats.utils.external_source_handling as esh
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.utils.settings import save_config, vara_cfg

LOG = logging.getLogger(__name__)

TEMPLATE_FOLDERS = ["projects", "experiments", "tables", "plots", "reports"]
# Template repository reference
TEMPLATE_REPO = "https://github.com/se-sic/varats-oot-template/tree/test-oot"


def validate_external_repo(repo_path: Path) -> tuple[bool, list[str]]:
    """
    Validate that the external repository follows the template structure.

    Args:
        repo_path: Path to the external repository root

    Returns:
        Tuple of (is_valid, missing_folders)
        - is_valid: True if all template folders exist
        - missing_folders: List of missing folders
    """
    if not repo_path.exists():
        return False, ["Repository path does not exist"]

    if not repo_path.is_dir():
        return False, ["Repository path is not a directory"]

    # Apply nested structure pattern: path/path_name/
    if not repo_path.exists():
        return False, [f"Nested structure not found at {repo_path}"]

    missing_folders = []
    for folder in TEMPLATE_FOLDERS:
        folder_path = repo_path / folder
        if not folder_path.exists():
            missing_folders.append(str(folder_path))

    is_valid = len(missing_folders) == 0
    return is_valid, missing_folders


def register_external_repository(repo_path: Path) -> None:
    """Add repo_path to config and save. Raises on failure."""
    current_repos = vara_cfg()['external_source_repositories'].value
    current_repos.append(str(repo_path))
    vara_cfg()['external_source_repositories'] = current_repos
    save_config()


def unregister_external_repository(repo_path: Path) -> None:
    """Add repo_path to config and save. Raises on failure."""
    current_repos = vara_cfg()['external_source_repositories'].value
    current_repos.remove(str(repo_path))
    vara_cfg()['external_source_repositories'] = current_repos
    save_config()


@click.group("vara-external")
def main() -> None:
    """
    Main function for managing external source repositories.

    `vara-external` provides commands to set up external repositories
    containing custom projects, experiments, tables, plots, and reports.
    """
    initialize_cli_tool()


@main.command("set")
@click.argument("path", type=click.Path(exists=True))
def _set_external_repository(path: str) -> None:
    """
    Set an external source repository.

    Validates that the repository follows the template structure and
    registers it in the VaRA configuration.

    Args:
        path: Path to the external repository root
    """
    repo_path = Path(path).resolve()

    # Validate repository structure
    is_valid, validation_errors = validate_external_repo(repo_path)

    current_repos = vara_cfg()['external_source_repositories'].value

    repo_is_registered = str(repo_path) in current_repos

    if not is_valid:
        msg_lines = [
            "Repository Not Complying To Template",
            f"  Repository path: {repo_path}",
            "  Missing or invalid folders:",
        ]
        for error in validation_errors:
            msg_lines.append(f"    - {error}")

        msg_lines.append("")
        msg_lines.append(f"  Template example: {TEMPLATE_REPO}")
        msg_lines.append("  Expected structure:")

        for folder in TEMPLATE_FOLDERS:
            msg_lines.append(f"    {repo_path / folder}")

        if repo_is_registered:
            if click.confirm(
                "The repository is already registered but does not match the template. "
                "Unregister it from the configuration?",
                default=False,
            ):
                unregister_external_repository(repo_path=repo_path)
                LOG.info(f"Unregistered invalid external repository: {repo_path}")
            return

        raise click.ClickException("\n".join(msg_lines))

    if repo_is_registered:
        LOG.info(f"Repository already registered at: {repo_path}")
        return

    # Add repository to config
    try:
        register_external_repository(repo_path=repo_path)
        LOG.info(f"Success - External repository configured at: {repo_path}")
    except Exception as exc:
        raise click.ClickException(
            f"Failure - Could not set external repository configuration: {exc}"
        ) from exc
