"""Test VaRA project utilities."""
import tempfile
import unittest
import unittest.mock as mock
from os.path import isdir
from pathlib import Path

from benchbuild.utils.cmd import git, mkdir, cp
from plumbum import local

from tests.test_utils import replace_config
from varats.project.project_util import (
    VaraTestRepoSource,
    VaraTestRepoSubmodule,
)


class TestVaraTestRepoSource(unittest.TestCase):
    """Test if directories and files of a VaraTestRepoSource and its
    VaraTestRepoSubmodules are correctly set up."""

    @classmethod
    def setUp(cls) -> None:
        """Define a multi library example repo."""

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
    def test_fetch_and_version(
        self, mock_tgt_prefix_base, mock_tgt_prefix_project_util
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with replace_config(tmp_path=tmppath):
                with local.cwd(tmpdir):
                    bb_tmp_path = Path("benchbuild/tmp")
                    bb_result_report_path = Path(
                        "benchbuild/results/GenerateBlameReport"
                    )
                    bb_result_lib_path = Path(
                        bb_result_report_path /
                        "TwoLibsOneProjectInteractionDiscreteLibsSingle"
                        "Project-cpp_projects@e64923e69e" /
                        "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
                    )
                    mock_tgt_prefix_base.return_value = tmppath / bb_tmp_path
                    mock_tgt_prefix_project_util.return_value = \
                        tmppath / bb_tmp_path

                    mkdir("-p", bb_result_report_path)
                    mkdir(bb_tmp_path)

                    self.elementalist.fetch()
                    self.elementalist.version(
                        bb_result_report_path / Path(
                            "TwoLibsOneProjectInteractionDiscreteLibsSingle"
                            "Project-cpp_projects@e64923e69e",
                            version="e64923e69e"
                        )
                    )

                    # Are directories present?
                    self.assertTrue(
                        isdir(
                            bb_tmp_path /
                            "TwoLibsOneProjectInteractionDiscreteLibsSingle"
                            "Project"
                        )
                    )
                    self.assertTrue(isdir(bb_result_lib_path))
                    self.assertTrue(isdir(bb_result_lib_path / "Elementalist"))
                    self.assertTrue(isdir(bb_result_lib_path / "fire_lib"))
                    self.assertTrue(isdir(bb_result_lib_path / "water_lib"))
                    self.assertTrue(
                        isdir(
                            bb_result_lib_path / "Elementalist" / "external" /
                            "fire_lib"
                        )
                    )
                    self.assertTrue(
                        isdir(
                            bb_result_lib_path / "Elementalist" / "external" /
                            "water_lib"
                        )
                    )

                    # Are .gitted files correctly renamed?
                    self.assertTrue(
                        isdir(bb_result_lib_path / "Elementalist" / ".git")
                    )
                    self.assertTrue(
                        isdir(bb_result_lib_path / "fire_lib" / ".git")
                    )
                    self.assertTrue(
                        isdir(bb_result_lib_path / "water_lib" / ".git")
                    )
                    self.assertTrue(
                        (bb_result_lib_path / "Elementalist" /
                         ".gitmodules").exists()
                    )

                    # Are repositories checked out at correct commit hash?
                    with local.cwd(bb_result_lib_path / "Elementalist"):
                        self.assertEqual(
                            "e64923e",
                            git('rev-parse', '--short', 'HEAD').rstrip()
                        )

                    with local.cwd(bb_result_lib_path / "fire_lib"):
                        self.assertEqual(
                            "ead5e00",
                            git('rev-parse', '--short', 'HEAD').rstrip()
                        )

                    with local.cwd(bb_result_lib_path / "water_lib"):
                        self.assertEqual(
                            "58ec513",
                            git('rev-parse', '--short', 'HEAD').rstrip()
                        )
