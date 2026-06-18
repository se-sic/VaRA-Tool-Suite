"""
Tests for the vara-external driver tool.
"""

import logging
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from tests.helper_utils import ExternalRepoFixture, run_in_test_environment
from varats.tools import driver_external
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


class TestValidateExternalRepo(unittest.TestCase):
    """Unit tests for validate_external_repo function."""

    def test_incorrect_repo_path(self) -> None:
        """Non-existent path returns False with appropriate error message."""
        non_existent_path = Path("/non/existent/path/that/should/not/exist")
        is_valid, errors = driver_external.validate_external_repo(
            non_existent_path
        )

        self.assertFalse(is_valid)
        self.assertIn("Repository path does not exist", errors)

    def test_repo_not_being_directory(self) -> None:
        """Path pointing to a file returns False with appropriate error message."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            file_path = tmp_path / "not_a_directory.txt"
            file_path.touch()

            is_valid, errors = driver_external.validate_external_repo(file_path)

            self.assertFalse(is_valid)
            self.assertIn("Repository path is not a directory", errors)

    def test_invalid_structure(self) -> None:
        """Missing nested structure or template folders returns False."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create a directory without nested structure
            is_valid, errors = driver_external.validate_external_repo(tmp_path)

            self.assertFalse(is_valid)
            self.assertTrue(len(errors) > 0)

    @run_in_test_environment(ExternalRepoFixture())
    def test_valid_structure(self) -> None:
        repo_path = Path.cwd() / "external_repo"
        is_valid, errors = driver_external.validate_external_repo(repo_path)

        self.assertTrue(is_valid)
        self.assertEqual([], errors)


class TestRegisterExternalRepository(unittest.TestCase):
    """Unit tests for register_external_repository function."""

    @run_in_test_environment(ExternalRepoFixture())
    def test_config_updated_successfully(self) -> None:
        """Config is updated successfully with the correct path."""
        repo_path = Path.cwd() / "external_repo"

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
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create invalid repo (no nested structure)
            runner = CliRunner()
            result = runner.invoke(driver_external.main, ["set", str(tmp_path)])
            self.assertNotEqual(0, result.exit_code)
            self.assertLogs("Repository Not Complying To Template")

    @run_in_test_environment(ExternalRepoFixture())
    def test_already_registered_repo_not_duplicated(self) -> None:
        """Already registered repo is not duplicated."""
        repo_path = Path.cwd() / "external_repo"

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

    @run_in_test_environment(ExternalRepoFixture())
    def test_exception_caught_on_registration_failure(self) -> None:
        """Exception caught when register_external_repository fails."""
        repo_path = Path.cwd() / "external_repo"

        runner = CliRunner()

        # Mock register_external_repository to raise an exception
        with patch(
            'varats.tools.driver_external.register_external_repository',
            side_effect=Exception("Mock config write failure"),
        ):
            result = runner.invoke(
                driver_external.main, ["set", str(repo_path)]
            )

        # Verify exit code is non-zero and error message is shown
        self.assertNotEqual(0, result.exit_code)
        self.assertLogs("Could not set external repository configuration")

    @run_in_test_environment(ExternalRepoFixture())
    def test_first_repo_added_successfully(self) -> None:
        """First repo with valid structure is added successfully."""
        repo_path = Path.cwd() / "external_repo"

        runner = CliRunner()
        result = runner.invoke(driver_external.main, ["set", str(repo_path)])

        self.assertEqual(0, result.exit_code)

        # Verify repo is in config
        repos = vara_cfg()['external_source_repositories'].value
        self.assertIn(str(Path(repo_path).resolve()), repos)

    @run_in_test_environment(ExternalRepoFixture())
    def test_additional_repos_added_successfully(self) -> None:
        """Additional distinct repos with valid structure are also added successfully."""
        runner = CliRunner()
        repo_paths = []

        repo_path1 = Path.cwd() / "external_repo"
        result1 = runner.invoke(driver_external.main, ["set", str(repo_path1)])
        self.assertEqual(0, result1.exit_code)
        repo_paths.append(repo_path1)

        # Re-copy the fixture into a second directory for a distinct repo.
        second_repo = Path.cwd() / "external_repo_second"
        shutil.copytree(repo_path1, second_repo)
        repo_path2 = second_repo
        result2 = runner.invoke(driver_external.main, ["set", str(repo_path2)])
        self.assertEqual(0, result2.exit_code)
        repo_paths.append(repo_path2)

        # Verify both repos are in config
        repos = vara_cfg()['external_source_repositories'].value
        for repo_path in repo_paths:
            self.assertIn(str(Path(repo_path).resolve()), repos)

        self.assertEqual(len(repo_paths), len(repos))

    @run_in_test_environment(ExternalRepoFixture())
    def test_invalid_registered_repo_unregistered_on_confirm(self) -> None:
        """Invalid registered repo is removed when the user confirms unregistering it."""
        repo_path = Path.cwd() / "external_repo"

        runner = CliRunner()

        # Register the repo while it is valid.
        register_result = runner.invoke(
            driver_external.main, ["set", str(repo_path)]
        )
        self.assertEqual(0, register_result.exit_code)

        # Break the structure so validation fails on the next invocation.
        shutil.rmtree(repo_path / driver_external.TEMPLATE_FOLDERS[0])

        result = runner.invoke(
            driver_external.main, ["set", str(repo_path)], input="y\n"
        )

        self.assertEqual(0, result.exit_code)
        self.assertLogs("Unregistered invalid external repository")

        repos = vara_cfg()["external_source_repositories"].value
        self.assertNotIn(str(repo_path), repos)

    @run_in_test_environment(ExternalRepoFixture())
    def test_invalid_registered_repo_kept_on_decline(self) -> None:
        """Invalid registered repo stays registered when the user declines unregistering it."""
        repo_path = Path.cwd() / "external_repo"

        runner = CliRunner()

        # Register the repo while it is valid.
        register_result = runner.invoke(
            driver_external.main, ["set", str(repo_path)]
        )
        self.assertEqual(0, register_result.exit_code)

        # Break the structure so validation fails on the next invocation.
        shutil.rmtree(repo_path / driver_external.TEMPLATE_FOLDERS[0])

        result = runner.invoke(
            driver_external.main, ["set", str(repo_path)], input="n\n"
        )

        self.assertEqual(0, result.exit_code)
        self.assertNoLogs()

        repos = vara_cfg()["external_source_repositories"].value
        self.assertIn(str(Path(repo_path).resolve()), repos)
