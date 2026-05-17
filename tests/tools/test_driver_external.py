"""
Tests for the vara-external driver tool.
"""
import logging
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from tests.helper_utils import run_in_test_environment
from varats.tools import driver_external
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


def create_mock_external_repo(tmp_path: Path) -> Path:
    """
    Create a mock external repository with required template structure.

    Args:
        tmp_path: Temporary directory path for creating the mock repo

    Returns:
        Path to the mock repository root
    """
    # Create non-nested (flat) structure: template folders directly under tmp_path
    root = tmp_path
    root.mkdir(parents=True, exist_ok=True)

    # Create template folders
    for folder in driver_external.TEMPLATE_FOLDERS:
        (root / folder).mkdir(exist_ok=True)

    return tmp_path


class TestValidateExternalRepo(unittest.TestCase):
    """Unit tests for validate_external_repo function."""

    def test_incorrect_repo_path(self) -> None:
        """Non-existent path returns False with appropriate error message."""
        non_existent_path = Path("/non/existent/path/that/should/not/exist")
        is_valid, errors = driver_external.validate_external_repo(non_existent_path)

        self.assertFalse(is_valid)
        self.assertIn("Repository path does not exist", errors)

    def test_repo_not_being_directory(self) -> None:
        """Path pointing to a file returns False with appropriate error message."""
        tmp_path = Path(tempfile.mkdtemp())

        file_path = tmp_path / "not_a_directory.txt"
        file_path.touch()

        is_valid, errors = driver_external.validate_external_repo(file_path)

        self.assertFalse(is_valid)
        self.assertIn("Repository path is not a directory", errors)

    @run_in_test_environment()
    def test_invalid_structure(self) -> None:
        """Missing nested structure or template folders returns False."""
        tmp_path = Path(tempfile.mkdtemp())

        # Create a directory without nested structure
        is_valid, errors = driver_external.validate_external_repo(tmp_path)

        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)


class TestRegisterExternalRepository(unittest.TestCase):
    """Unit tests for register_external_repository function."""

    @run_in_test_environment()
    def test_config_updated_successfully(self) -> None:
        """Config is updated successfully with the correct path."""
        tmp_path = Path(tempfile.mkdtemp())

        # Create a valid mock repository
        repo_path = create_mock_external_repo(tmp_path)

        # Get initial config state
        initial_repos = vara_cfg()['external_source_repositories'].value.copy()

        # Register the repository
        driver_external.register_external_repository(repo_path)

        # Verify config was updated
        updated_repos = vara_cfg()['external_source_repositories'].value
        self.assertIn(str(repo_path), updated_repos)
        self.assertEqual(len(updated_repos), len(initial_repos) + 1)


class TestDriverExternal(unittest.TestCase):
    """Integration tests for vara-external set command."""

    @run_in_test_environment()
    def test_invalid_file_structure(self) -> None:
        """Correct output when invalid file structure."""
        tmp_path = Path(tempfile.mkdtemp())

        # Create invalid repo (no nested structure)
        runner = CliRunner()
        result = runner.invoke(driver_external.main, ["set", str(tmp_path)])
        self.assertNotEqual(0, result.exit_code)
        self.assertLogs("Repository Not Complying To Template")

    @run_in_test_environment()
    def test_already_registered_repo_not_duplicated(self) -> None:
        """Already registered repo is not duplicated."""
        tmp_path = Path(tempfile.mkdtemp())

        # Create valid repo
        repo_path = create_mock_external_repo(tmp_path)

        runner = CliRunner()

        # Register repo first time
        result1 = runner.invoke(driver_external.main, ["set", str(repo_path)])
        self.assertEqual(0, result1.exit_code)

        # Try to register same repo again
        result2 = runner.invoke(driver_external.main, ["set", str(repo_path)])
        self.assertEqual(0, result2.exit_code)
        self.assertLogs("already registered")

        # Verify repo appears only once in config
        repos = vara_cfg()['external_source_repositories'].value
        repo_count = sum(1 for r in repos if str(repo_path) in r)
        self.assertEqual(1, repo_count)

    @run_in_test_environment()
    def test_exception_caught_on_registration_failure(self) -> None:
        """Exception caught when register_external_repository fails."""
        tmp_path = Path(tempfile.mkdtemp())
        repo_path = create_mock_external_repo(tmp_path)

        runner = CliRunner()

        # Mock register_external_repository to raise an exception
        with patch(
            'varats.tools.driver_external.register_external_repository',
            side_effect=Exception("Mock config write failure"),
        ):
            result = runner.invoke(driver_external.main, ["set", str(repo_path)])

        # Verify exit code is non-zero and error message is shown
        self.assertNotEqual(0, result.exit_code)
        self.assertLogs("Could not set external repository configuration")

    @run_in_test_environment()
    def test_first_repo_added_successfully(self) -> None:
        """First repo with valid structure is added successfully."""
        tmp_path = Path(tempfile.mkdtemp())

        # Create valid repo
        repo_path = create_mock_external_repo(tmp_path)

        runner = CliRunner()
        result = runner.invoke(driver_external.main, ["set", str(repo_path)])

        self.assertEqual(0, result.exit_code)

        # Verify repo is in config
        repos = vara_cfg()['external_source_repositories'].value
        self.assertIn(str(Path(repo_path).resolve()), repos)

    @run_in_test_environment()
    def test_additional_repos_added_successfully(self) -> None:
        """Additional distinct repos with valid structure are also added successfully."""
        runner = CliRunner()
        repo_paths = []

        # Add first repo
        tmp_path1 = Path(tempfile.mkdtemp())
        repo_path1 = create_mock_external_repo(tmp_path1)
        result1 = runner.invoke(driver_external.main, ["set", str(repo_path1)])
        self.assertEqual(0, result1.exit_code)
        repo_paths.append(repo_path1)

        # Add second repo
        tmp_path2 = Path(tempfile.mkdtemp())
        repo_path2 = create_mock_external_repo(tmp_path2)
        result2 = runner.invoke(driver_external.main, ["set", str(repo_path2)])
        self.assertEqual(0, result2.exit_code)
        repo_paths.append(repo_path2)

        # Verify both repos are in config
        repos = vara_cfg()['external_source_repositories'].value
        for repo_path in repo_paths:
            self.assertIn(str(Path(repo_path).resolve()), repos)

        self.assertEqual(len(repo_paths), len(repos))

    @run_in_test_environment()
    def test_invalid_registered_repo_unregistered_on_confirm(self) -> None:
        """Invalid registered repo is removed when the user confirms unregistering it."""
        tmp_path = Path(tempfile.mkdtemp())
        repo_path = create_mock_external_repo(tmp_path)

        runner = CliRunner()

        # Register the repo while it is valid.
        register_result = runner.invoke(driver_external.main, ["set", str(repo_path)])
        self.assertEqual(0, register_result.exit_code)

        # Break the structure so validation fails on the next invocation.
        shutil.rmtree(repo_path / driver_external.TEMPLATE_FOLDERS[0])

        with patch("varats.tools.driver_external.click.confirm", return_value=True):
            result = runner.invoke(driver_external.main, ["set", str(repo_path)])

        self.assertEqual(0, result.exit_code)
        self.assertLogs("Unregistered invalid external repository")

        repos = vara_cfg()["external_source_repositories"].value
        self.assertNotIn(str(repo_path), repos)

    @run_in_test_environment()
    def test_invalid_registered_repo_kept_on_decline(self) -> None:
        """Invalid registered repo stays registered when the user declines unregistering it."""
        tmp_path = Path(tempfile.mkdtemp())
        repo_path = create_mock_external_repo(tmp_path)

        runner = CliRunner()

        # Register the repo while it is valid.
        register_result = runner.invoke(driver_external.main, ["set", str(repo_path)])
        self.assertEqual(0, register_result.exit_code)

        # Break the structure so validation fails on the next invocation.
        shutil.rmtree(repo_path / driver_external.TEMPLATE_FOLDERS[0])

        with patch("varats.tools.driver_external.click.confirm", return_value=False):
            result = runner.invoke(driver_external.main, ["set", str(repo_path)])

        self.assertEqual(0, result.exit_code)
        self.assertNoLogs()

        repos = vara_cfg()["external_source_repositories"].value
        self.assertIn(str(Path(repo_path).resolve()), repos)
