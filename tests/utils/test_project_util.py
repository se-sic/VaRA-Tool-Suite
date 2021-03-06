"""Test VaRA project utilities."""
import tempfile
import typing as tp
import unittest
import unittest.mock as mock
from os.path import isdir
from pathlib import Path

from benchbuild.utils.cmd import git, mkdir
from plumbum import local

from tests.test_utils import replace_config
from varats.project.project_util import (
    VaraTestRepoSource,
    VaraTestRepoSubmodule,
)
from varats.tools.bb_config import generate_benchbuild_config


class TestVaraTestRepoSource(unittest.TestCase):
    """Test if directories and files of a VaraTestRepoSource and its
    VaraTestRepoSubmodules are correctly set up."""

    @classmethod
    def setUp(cls) -> None:
        """Define a multi library example repo."""

        cls.revision = "e64923e69e"

        cls.bb_tmp_path = Path("benchbuild/tmp")
        cls.bb_result_report_path = Path(
            "benchbuild/results/GenerateBlameReport"
        )
        cls.bb_result_lib_path = Path(
            cls.bb_result_report_path /
            f"TwoLibsOneProjectInteractionDiscreteLibsSingle"
            f"Project-cpp_projects@{cls.revision}" /
            "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
        )

        cls.elementalist = VaraTestRepoSource(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/Elementalist",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/Elementalist",
            refspec="HEAD",
            limit=None,
            shallow=False,
        )

        cls.fire_lib = VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/fire_lib",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/fire_lib",
            refspec="HEAD",
            limit=None,
            shallow=False,
        )

        cls.water_lib = VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/water_lib",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/water_lib",
            refspec="HEAD",
            limit=None,
            shallow=False,
        )

    @mock.patch('benchbuild.source.base.target_prefix')
    @mock.patch('varats.project.project_util.target_prefix')
    def test_vara_test_repo_dir_creation(
        self, mock_tgt_prefix_base, mock_tgt_prefix_project_util
    ) -> None:
        """Test if the needed directories of the main repo and its submodules
        are present."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with replace_config(tmp_path=tmppath):
                with local.cwd(tmpdir):
                    mock_tgt_prefix_base.return_value = \
                        tmppath / self.bb_tmp_path
                    mock_tgt_prefix_project_util.return_value = \
                        tmppath / self.bb_tmp_path

                    mkdir("-p", self.bb_result_report_path)
                    mkdir(self.bb_tmp_path)

                    self.elementalist.fetch()
                    self.elementalist.version(
                        self.bb_result_report_path / Path(
                            f"TwoLibsOneProjectInteractionDiscreteLibsSingle"
                            f"Project-cpp_projects@{self.revision}",
                            version=self.revision
                        )
                    )

                    # Are directories present?
                    self.assertTrue(
                        isdir(
                            self.bb_tmp_path /
                            "TwoLibsOneProjectInteractionDiscreteLibsSingle"
                            "Project"
                        )
                    )
                    self.assertTrue(isdir(self.bb_result_lib_path))
                    self.assertTrue(
                        isdir(self.bb_result_lib_path / "Elementalist")
                    )
                    self.assertTrue(isdir(self.bb_result_lib_path / "fire_lib"))
                    self.assertTrue(
                        isdir(self.bb_result_lib_path / "water_lib")
                    )
                    self.assertTrue(
                        isdir(
                            self.bb_result_lib_path / "Elementalist" /
                            "external" / "fire_lib"
                        )
                    )
                    self.assertTrue(
                        isdir(
                            self.bb_result_lib_path / "Elementalist" /
                            "external" / "water_lib"
                        )
                    )

    @mock.patch('benchbuild.source.base.target_prefix')
    @mock.patch('varats.project.project_util.target_prefix')
    def test_vara_test_repo_gitted_renaming(
        self, mock_tgt_prefix_base, mock_tgt_prefix_project_util
    ) -> None:
        """Test if the .gitted files are correctly renamed back to their
        original git name."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with replace_config(tmp_path=tmppath):
                with local.cwd(tmpdir):
                    mock_tgt_prefix_base.return_value = \
                        tmppath / self.bb_tmp_path
                    mock_tgt_prefix_project_util.return_value = \
                        tmppath / self.bb_tmp_path

                    self.elementalist.fetch()
                    self.elementalist.version(
                        self.bb_result_report_path / Path(
                            f"TwoLibsOneProjectInteractionDiscreteLibsSingle"
                            f"Project-cpp_projects@{self.revision}",
                            version=self.revision
                        )
                    )

                    # Are .gitted files correctly renamed?
                    self.assertTrue(
                        isdir(
                            self.bb_result_lib_path / "Elementalist" / ".git"
                        )
                    )
                    self.assertTrue(
                        isdir(self.bb_result_lib_path / "fire_lib" / ".git")
                    )
                    self.assertTrue(
                        isdir(self.bb_result_lib_path / "water_lib" / ".git")
                    )
                    self.assertTrue((
                        self.bb_result_lib_path / "Elementalist" / ".gitmodules"
                    ).exists())

    @mock.patch('benchbuild.source.base.target_prefix')
    @mock.patch('varats.project.project_util.target_prefix')
    def test_vara_test_repo_lib_checkout(
        self, mock_tgt_prefix_base, mock_tgt_prefix_project_util
    ) -> None:
        """Test if the repositories are checked out at the specified
        revision."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with replace_config(tmp_path=tmppath):
                with local.cwd(tmpdir):
                    mock_tgt_prefix_base.return_value = \
                        tmppath / self.bb_tmp_path
                    mock_tgt_prefix_project_util.return_value = \
                        tmppath / self.bb_tmp_path

                    self.elementalist.fetch()
                    self.elementalist.version(
                        self.bb_result_report_path / Path(
                            f"TwoLibsOneProjectInteractionDiscreteLibsSingle"
                            f"Project-cpp_projects@{self.revision}",
                            version=self.revision
                        )
                    )

                    # Are repositories checked out at correct commit hash?
                    with local.cwd(self.bb_result_lib_path / "Elementalist"):
                        self.assertEqual(
                            "5e8fe16",
                            git('rev-parse', '--short', 'HEAD').rstrip()
                        )

                    with local.cwd(self.bb_result_lib_path / "fire_lib"):
                        self.assertEqual(
                            "ead5e00",
                            git('rev-parse', '--short', 'HEAD').rstrip()
                        )

                    with local.cwd(self.bb_result_lib_path / "water_lib"):
                        self.assertEqual(
                            "58ec513",
                            git('rev-parse', '--short', 'HEAD').rstrip()
                        )

                    with local.cwd(self.bb_result_lib_path / "earth_lib"):
                        self.assertEqual(
                            "1db6fbe",
                            git('rev-parse', '--short', 'HEAD').rstrip()
                        )

    def test_if_project_names_are_well_formed(self) -> None:
        """Tests if project names are well formed, e.g., they must not contain a
        dash."""

        with replace_config(replace_bb_config=True) as (vara_cfg, bb_cfg):
            tmp_file = tempfile.NamedTemporaryFile()
            generate_benchbuild_config(vara_cfg, tmp_file.name)
            bb_cfg.load(tmp_file.name)
            loaded_project_paths: tp.List[str] = bb_cfg["plugins"]["projects"
                                                                  ].value

        loaded_project_names = [
            project_path.rsplit(sep='.', maxsplit=1)[1]
            for project_path in loaded_project_paths
        ]
        for project_name in loaded_project_names:
            if '-' in project_name:
                self.fail(
                    f"The project name {project_name} must not contain the "
                    f"dash character."
                )
