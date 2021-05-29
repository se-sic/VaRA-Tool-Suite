"""Test module for settings."""
import pkgutil
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

        for _, plugin_name, is_pkg in pkgutil.walk_packages([package_name]):
            qname = f"{package_name}/{plugin_name}"
            if qname in exclude_list:
                continue

            if is_pkg:
                self.check_all_files_in_config_list(
                    qname, config_list, exclude_list
                )
            else:
                self.assertTrue(qname in config_list, "Missing: " + plugin_name)

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
            "varats.experiments.vara.blame_experiment"
        ]

        loaded_plugins = bb_cfg()["plugins"]["experiments"].value
        self.check_all_files_in_config_list(
            "varats.experiments", loaded_plugins, excluded_experiments
        )
