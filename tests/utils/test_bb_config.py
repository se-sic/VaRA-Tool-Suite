"""Test module for settings."""

import importlib
import pkgutil
import sys
import unittest

from tests.helper_utils import run_in_test_environment
from varats.tools.bb_config import update_env
from varats.utils import settings
from varats.utils.settings import bb_cfg, vara_cfg


class BenchBuildConfig(unittest.TestCase):
    """Test BenchBuild config."""

    def check_all_files_in_config_list(
        self,
        package_name: str,
        config_list: list[str],
        exclude_list: list[str] | None = None,
    ) -> None:
        """Check if all python files in a folder are added to the benchbuild
        project config."""
        if exclude_list is None:
            exclude_list = []

        importlib.import_module(package_name)
        path = getattr(sys.modules[package_name], '__path__', None) or []
        for _, plugin_name, is_pkg in pkgutil.walk_packages(
            path, f"{package_name}."
        ):
            if plugin_name in exclude_list:
                continue

            if is_pkg:
                self.check_all_files_in_config_list(
                    plugin_name, config_list, exclude_list
                )
            else:
                self.assertIn(plugin_name, config_list)

    @run_in_test_environment()
    def test_if_all_nodes_have_been_created(self) -> None:
        """Test if all the benchbuild config was created with all expected
        nodes."""

        self.assertTrue(bb_cfg()["varats"].__contains__("outfile"))
        self.assertTrue(bb_cfg()["varats"].__contains__("result"))

    @run_in_test_environment()
    def test_if_slurm_config_was_added(self) -> None:
        """Test if all the benchbuild slurm config was created."""

        self.assertTrue(bb_cfg()["slurm"].__contains__("account"))
        self.assertTrue(bb_cfg()["slurm"].__contains__("partition"))

    @run_in_test_environment()
    def test_if_projects_were_added(self) -> None:
        """Test if all projects were added to the benchbuild config."""
        excluded_projects = ["varats.experiments.c_projects.glibc"]

        loaded_plugins = bb_cfg()["plugins"]["projects"].value
        self.check_all_files_in_config_list(
            "varats.projects.c_projects", loaded_plugins, excluded_projects
        )
        self.check_all_files_in_config_list(
            "varats.projects.cpp_projects", loaded_plugins, excluded_projects
        )
        self.check_all_files_in_config_list(
            "varats.projects.perf_tests", loaded_plugins, excluded_projects
        )

    @run_in_test_environment()
    def test_if_experiments_were_added(self) -> None:
        """Test if all projects were added to the benchbuild config."""
        excluded_experiments = [
            "varats.experiments.discover_experiments",
            "varats.experiments.vara.region_instrumentation",
            "varats.experiments.vara.commit_annotation_report",
            "varats.experiments.vara.blame_experiment",
            "varats.experiments.vara.feature_experiment",
        ]

        loaded_plugins = bb_cfg()["plugins"]["experiments"].value
        self.check_all_files_in_config_list(
            "varats.experiments", loaded_plugins, excluded_experiments
        )

    @run_in_test_environment()
    def test_if_environment_updates_correctly(self) -> None:
        """Test if the environment variables are updated correctly."""
        config = bb_cfg()
        config["env"] = {"PATH": ["/old/"], "LD_PATH": ["/ld/"]}
        vara_cfg()["vara"]["llvm_install_dir"] = "/test/"
        update_env(config)
        self.assertEqual(config["env"].value["PATH"], ["/test/bin", "/old/"])
        self.assertEqual(config["env"].value["LD_PATH"], ["/ld/"])

    def test_bb_cfg_function_calls(self) -> None:
        """Test if the bb_cfg function returns the correct config."""
        cfg = bb_cfg()
        self.assertEqual(cfg, settings._BB_CFG)

    def test_change_value_kwargs(self) -> None:
        """Test if the change_value function updates the config correctly."""
        with bb_cfg(tmp_dir="/new/tmp/dir") as cfg:
            self.assertEqual(str(cfg["tmp_dir"]), "/new/tmp/dir")

    def test_change_value_kwargs_without_obj(self) -> None:
        """Test config update without using the context manager object."""
        with bb_cfg(tmp_dir="/new/tmp/dir"):
            self.assertEqual(str(bb_cfg()["tmp_dir"]), "/new/tmp/dir")

    def test_value_restored_after_context(self) -> None:
        """Test if the config value is restored after the context manager."""
        original_tmp_dir = str(bb_cfg()["tmp_dir"])
        temporary_tmp_dir = str(settings.Path(original_tmp_dir) / "new/tmp/dir")

        with bb_cfg(tmp_dir=temporary_tmp_dir):
            self.assertEqual(str(bb_cfg()["tmp_dir"]), temporary_tmp_dir)

        self.assertEqual(str(bb_cfg()["tmp_dir"]), original_tmp_dir)

    def test_nested_value_change(self) -> None:
        """Test context managers restore nested config values correctly."""
        original_vara_ver = str(bb_cfg()["container"])

        with bb_cfg(container={"runroot": "new_directory"}):
            self.assertEqual(
                str(bb_cfg()["container"]["runroot"]), "new_directory"
            )

        self.assertEqual(str(bb_cfg()["container"]), original_vara_ver)

    def test_nested_config_change(self) -> None:
        """Test nested context managers restore nested config values."""
        original_vara_ver = str(bb_cfg()["container"])

        with bb_cfg(container={"runroot": "new_directory"}):
            self.assertEqual(
                str(bb_cfg()["container"]["runroot"]), "new_directory"
            )
            with bb_cfg(container={"runroot": "another_directory"}):
                self.assertEqual(
                    str(bb_cfg()["container"]["runroot"]), "another_directory"
                )
            self.assertEqual(
                str(bb_cfg()["container"]["runroot"]), "new_directory"
            )

        self.assertEqual(str(bb_cfg()["container"]), original_vara_ver)
