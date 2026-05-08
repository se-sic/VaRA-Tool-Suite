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

# TODO: Fetch template from template repo (https://github.com/se-sic/vara-test-repos)
# instead of hardcoding it
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
    # TODO: Extend validation to check folder contents (e.g., __init__.py files)

    if not repo_path.exists():
        return False, ["Repository path does not exist"]

    if not repo_path.is_dir():
        return False, ["Repository path is not a directory"]

    # Apply nested structure pattern: path/path_name/
    source_root = esh.determine_project_source_root(repo_path)

    if not source_root.exists():
        return False, [f"Nested structure not found at {source_root}"]

    missing_folders = []
    for folder in TEMPLATE_FOLDERS:
        folder_path = source_root / folder
        if not folder_path.exists():
            missing_folders.append(str(folder_path))

    is_valid = len(missing_folders) == 0
    return is_valid, missing_folders


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
        LOG.error("Repository Not Complying To Template")
        LOG.error(f"  Repository path: {repo_path}")
        LOG.error("  Missing or invalid folders:")
        for error in validation_errors:
            LOG.error(f"    - {error}")

        LOG.error(f"\n  Template example: {TEMPLATE_REPO}")
        LOG.error("  Expected structure:")
        source_root = esh.determine_project_source_root(repo_path)
        for folder in TEMPLATE_FOLDERS:
            LOG.error(f"    {source_root / folder}")

        # TODO: should we unregister the repo?
        if repo_is_registered:
            pass

        return

    if repo_is_registered:
        LOG.info(f"Repository already registered at: {repo_path}")
        return

    # Add repository to config
    try:
        current_repos.append(str(repo_path))
        vara_cfg()['external_source_repositories'] = current_repos
        save_config()
        LOG.info(f"Success - External repository configured at: {repo_path}")
    except Exception as exc:
        LOG.error(f"Failure - Could not set external repository configuration: {exc}")
        raise
