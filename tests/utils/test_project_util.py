"""Test VaRA project utilities."""
import tempfile
import unittest
import unittest.mock as mock
from os.path import isdir
from pathlib import Path

from benchbuild.utils.cmd import git, mkdir, cp
from plumbum import local

from tests.test_utils import replace_config
from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    VaraTestRepoSource,
    VaraTestRepoSubmodule,
)


class TestVaraTestRepoSource(unittest.TestCase):
    """Test if a VaraTestRepoSource is correctly set up with its submodules."""

    @classmethod
    def setUp(cls) -> None:
        """Set up a multi lib example repo with submodules."""

        cls.elementalist = VaraTestRepoSource(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/Elementalist",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/Elementalist",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            )
        )

        #cls.elementalist.fetch()

        cls.fire_lib = VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/fire_lib",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/fire_lib",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            )
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
            version_filter=project_filter_generator(
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            )
        )

    @mock.patch('benchbuild.source.base.target_prefix')
    @mock.patch('varats.project.project_util.target_prefix')
    def test_varatestreposource_with_submodules(
        self, mock_tgt_prefix_base, mock_tgt_prefix_project_util
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with replace_config(tmp_path=tmppath):
                with local.cwd(tmppath):
                    bb_tmp_path = Path("benchbuild/tmp")
                    bb_result_report_path = Path(
                        "benchbuild/results/GenerateBlameReport"
                    )
                    bb_result_lib_path = Path(
                        bb_result_report_path /
                        "TwoLibsOneProjectInteractionDiscreteLibsSingleProject-cpp_projects@e64923e69e"
                        /
                        "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
                    )
                    mock_tgt_prefix_base.return_value = tmppath / bb_tmp_path
                    mock_tgt_prefix_project_util.return_value = tmppath / bb_tmp_path

                    mkdir("-p", bb_result_report_path)
                    mkdir(bb_tmp_path)

                    self.elementalist.fetch()
                    self.elementalist.version(
                        bb_result_report_path / Path(
                            "TwoLibsOneProjectInteractionDiscreteLibsSingleProject-cpp_projects@e64923e69e",
                            version="e64923e69e"
                        )
                    )

                    # Are directories present?
                    self.assertTrue(
                        isdir(
                            bb_tmp_path /
                            "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
                        )
                    )
                    self.assertTrue(isdir(bb_result_lib_path))
                    self.assertTrue(isdir(bb_result_lib_path / "Elementalist"))
                    self.assertTrue(isdir(bb_result_lib_path / "fire_lib"))
                    self.assertTrue(isdir(bb_result_lib_path / "water_lib"))

                    # Are submodules present?
                    self.assertTrue(isdir(bb_result_lib_path / "Elementalist"))

                    # Are files correctly renamed?
                    self.assertTrue(
                        isdir(bb_result_lib_path / "Elementalist" / ".git")
                    )
                    self.assertTrue(
                        isdir(bb_result_lib_path / "fire_lib" / ".git")
                    )
                    self.assertTrue(
                        isdir(bb_result_lib_path / "water_lib" / ".git")
                    )
