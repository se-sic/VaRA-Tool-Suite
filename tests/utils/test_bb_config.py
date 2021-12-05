"""Test module for settings."""
import importlib
import pkgutil
import sys
import typing as tp
import unittest

from tests.test_utils import run_in_test_environment
from varats.utils.settings import bb_cfg


class BenchBuildConfig(unittest.TestCase):
    """Test BenchBuild config."""

    def check_all_files_in_config_list(
        self,
        package_name: str,
        config_list: tp.List[str],
        exclude_list: tp.Optional[tp.List[str]] = None
    ):
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
    def test_if_all_nodes_have_been_created(self):
        """Test if all the benchbuild config was created with all expected
        nodes."""

        self.assertTrue(bb_cfg()["varats"].__contains__("outfile"))
        self.assertTrue(bb_cfg()["varats"].__contains__("result"))

    @run_in_test_environment()
    def test_if_slurm_config_was_added(self):
        """Test if all the benchbuild slurm config was created."""

        self.assertTrue(bb_cfg()["slurm"].__contains__("account"))
        self.assertTrue(bb_cfg()["slurm"].__contains__("partition"))

    @run_in_test_environment()
    def test_if_projects_were_added(self):
        """Test if all projects were added to the benchbuild config."""
        excluded_projects = ["varats.experiments.c_projects.glibc"]

        loaded_plugins = bb_cfg()["plugins"]["projects"].value
        self.check_all_files_in_config_list(
            "varats.projects.c_projects", loaded_plugins, excluded_projects
        )
        self.check_all_files_in_config_list(
            "varats.projects.cpp_projects", loaded_plugins, excluded_projects
        )

    @run_in_test_environment()
    def test_if_experiments_were_added(self):
        """Test if all projects were added to the benchbuild config."""
        excluded_experiments = [
            "varats.experiments.vara.region_instrumentation",
            "varats.experiments.vara.commit_annotation_report",
            "varats.experiments.vara.blame_experiment",
            "varats.experiments.phasar.incremental_analysis"
        ]

        loaded_plugins = bb_cfg()["plugins"]["experiments"].value
        self.check_all_files_in_config_list(
            "varats.experiments", loaded_plugins, excluded_experiments
        )
