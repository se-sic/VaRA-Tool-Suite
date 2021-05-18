"""Test module for settings."""
import os
import unittest
from pathlib import Path

from varats.tools.bb_config import create_new_bb_config
from varats.utils.settings import create_new_varats_config


class BenchBuildConfig(unittest.TestCase):
    """Test BenchBuild config."""

    @classmethod
    def setUpClass(cls):
        """Setup and generate the benchbuild config file."""
        varats_cfg = create_new_varats_config()
        cls.bb_cfg = create_new_bb_config(varats_cfg)

    def check_all_files_in_config_list(
        self, folder, config_list, exclude_list=None
    ):
        """Check if all python files in a folder are added to the benchbuild
        project config."""
        if exclude_list is None:
            exclude_list = []

        for plugin_file in os.listdir(Path("varats") / folder):
            if plugin_file in exclude_list:
                continue

            if os.path.isfile(folder + plugin_file) and\
                    plugin_file.endswith(".py") and\
                    plugin_file != "__init__.py":
                plugin_python_path = (folder + plugin_file)\
                    .replace(".py", "")\
                    .replace("/", ".")
                self.assertTrue(
                    plugin_python_path in config_list,
                    "Missing: " + plugin_python_path
                )

    def test_if_all_nodes_have_been_created(self):
        """Test if all the benchbuild config was created with all expected
        nodes."""

        self.assertTrue(self.bb_cfg["varats"].__contains__("outfile"))
        self.assertTrue(self.bb_cfg["varats"].__contains__("result"))

    def test_if_slurm_config_was_added(self):
        """Test if all the benchbuild slurm config was created."""

        self.assertTrue(self.bb_cfg["slurm"].__contains__("account"))
        self.assertTrue(self.bb_cfg["slurm"].__contains__("partition"))

    def test_if_projects_were_added(self):
        """Test if all projects where added to the benchbuild config."""
        excluded_projects = [
            "llvm-all.py", "llvm-min.py", "llvm.py", "glibc.py"
        ]

        loaded_plugins = self.bb_cfg["plugins"]["projects"].value
        self.check_all_files_in_config_list(
            "varats/projects/c_projects/", loaded_plugins, excluded_projects
        )
        self.check_all_files_in_config_list(
            "varats/projects/cpp_projects/", loaded_plugins, excluded_projects
        )

    def test_if_experiments_were_added(self):
        """Test if all projects where added to the benchbuild config."""
        excluded_experiments = [
            "wllvm.py", "phasar.py", "region_instrumentation.py",
            "commit_annotation_report.py", "blame_experiment.py"
        ]

        loaded_plugins = self.bb_cfg["plugins"]["experiments"].value
        self.check_all_files_in_config_list(
            "varats/experiments/", loaded_plugins, excluded_experiments
        )
