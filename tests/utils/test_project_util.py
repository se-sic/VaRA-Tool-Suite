"""Test VaRA project utilities."""
import typing as tp
import unittest
from os.path import isdir
from pathlib import Path

from benchbuild.utils.cmd import git, mkdir
from plumbum import local

from tests.test_utils import run_in_test_environment, UnitTestFixtures
from varats.project.project_util import (
    get_project_cls_by_name,
    get_loaded_vara_projects,
    ProjectBinaryWrapper,
    BinaryType,
    get_tagged_commits,
    get_local_project_git_path,
)
from varats.projects.c_projects.gravity import Gravity
from varats.projects.discover_projects import initialize_projects
from varats.tools.bb_config import create_new_bb_config
from varats.ts_utils.project_sources import (
    VaraTestRepoSource,
    VaraTestRepoSubmodule,
)
from varats.utils.settings import create_new_varats_config, bb_cfg


class TestProjectLookup(unittest.TestCase):
    """Tests different project lookup methods."""

    @classmethod
    def setUp(cls) -> None:
        """Initialize all projects before running tests."""
        initialize_projects()

    def test_project_lookup_by_name(self) -> None:
        """Check if we can load project classes from their name."""
        grav_prj_cls = get_project_cls_by_name("gravity")

        self.assertEqual(grav_prj_cls, Gravity)

    def test_failed_project_lookup(self) -> None:
        """Check if we correctly fail, should a project be queried that does not
        exist."""
        self.assertRaises(
            LookupError, get_project_cls_by_name, "this_project_does_not_exists"
        )

    def test_project_iteration(self) -> None:
        """Check if we can iterate over loaded vara projects."""
        found_gravity = False
        for prj_cls in get_loaded_vara_projects():
            if prj_cls.NAME == "gravity":
                found_gravity = True

        self.assertTrue(found_gravity)


class TestVaraTestRepoSource(unittest.TestCase):
    """Test if directories and files of a VaraTestRepoSource and its
    VaraTestRepoSubmodules are correctly set up."""

    revision: tp.ClassVar[str]
    bb_result_report_path: tp.ClassVar[Path]
    bb_result_lib_path: tp.ClassVar[Path]
    elementalist: tp.ClassVar[VaraTestRepoSource]
    fire_lib: tp.ClassVar[VaraTestRepoSubmodule]
    water_lib: tp.ClassVar[VaraTestRepoSubmodule]

    @classmethod
    def setUp(cls) -> None:
        """Define a multi library example repo."""

        cls.revision = "e64923e69e"

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
            project_name="TwoLibsOneProjectInteractionDiscreteLibsSingleProject",
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/Elementalist",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/Elementalist",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )

        cls.fire_lib = VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/fire_lib",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/fire_lib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
        )

        cls.water_lib = VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/water_lib",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/water_lib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
        )

    @run_in_test_environment(UnitTestFixtures.TEST_PROJECTS)
    def test_vara_test_repo_dir_creation(self) -> None:
        """Test if the needed directories of the main repo and its submodules
        are present."""

        mkdir("-p", self.bb_result_report_path)

        self.elementalist.version(
            f"{self.bb_result_report_path}/"
            f"TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            f"-cpp_projects@{self.revision}",
            version=self.revision
        )

        # Are directories present?
        self.assertTrue(
            isdir(
                f"{str(bb_cfg()['tmp_dir'])}/"
                f"TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            )
        )
        self.assertTrue(isdir(self.bb_result_lib_path))
        self.assertTrue(isdir(self.bb_result_lib_path / "Elementalist"))
        self.assertTrue(isdir(self.bb_result_lib_path / "fire_lib"))
        self.assertTrue(isdir(self.bb_result_lib_path / "water_lib"))
        self.assertTrue(
            isdir(
                self.bb_result_lib_path / "Elementalist" / "external" /
                "fire_lib"
            )
        )
        self.assertTrue(
            isdir(
                self.bb_result_lib_path / "Elementalist" / "external" /
                "water_lib"
            )
        )

    @run_in_test_environment(UnitTestFixtures.TEST_PROJECTS)
    def test_vara_test_repo_gitted_renaming(self) -> None:
        """Test if the .gitted files are correctly renamed back to their
        original git name."""
        self.elementalist.version(
            f"{self.bb_result_report_path}/"
            f"TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            f"-cpp_projects@{self.revision}",
            version=self.revision
        )

        # Are .gitted files correctly renamed?
        self.assertTrue(
            isdir(self.bb_result_lib_path / "Elementalist" / ".git")
        )
        self.assertTrue(isdir(self.bb_result_lib_path / "fire_lib" / ".git"))
        self.assertTrue(isdir(self.bb_result_lib_path / "water_lib" / ".git"))
        self.assertTrue(
            (self.bb_result_lib_path / "Elementalist" / ".gitmodules").exists()
        )

    @run_in_test_environment(UnitTestFixtures.TEST_PROJECTS)
    def test_vara_test_repo_lib_checkout(self) -> None:
        """Test if the repositories are checked out at the specified
        revision."""
        self.elementalist.version(
            f"{self.bb_result_report_path}/"
            f"TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            f"-cpp_projects@{self.revision}",
            version=self.revision
        )

        # Are repositories checked out at correct commit hash?
        with local.cwd(self.bb_result_lib_path / "Elementalist"):
            self.assertEqual(
                self.revision[:7],
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
        """Tests if project names are well-formed, e.g., they must not contain a
        dash."""

        varats_cfg = create_new_varats_config()
        bb_cfg = create_new_bb_config(varats_cfg, True)
        loaded_project_paths: tp.List[str] = bb_cfg["plugins"]["projects"].value

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


class TestProjectBinaryWrapper(unittest.TestCase):
    """Test if we can correctly setup and use the RevisionBinaryMap."""

    def test_execution_of_executable(self) -> None:
        """Check if we can execute an executable binary."""
        binary = ProjectBinaryWrapper(
            "ls", Path("/bin/ls"), BinaryType.EXECUTABLE
        )

        ret = binary()
        self.assertIsNotNone(ret)
        self.assertIsInstance(ret, str)

    def test_execution_of_libraries(self) -> None:
        """Check whether we fail when executing a shared/static library."""
        static_lib_binary = ProjectBinaryWrapper(
            "ls", Path("/bin/ls"), BinaryType.STATIC_LIBRARY
        )
        self.assertIsNone(static_lib_binary())

        shared_lib_binary = ProjectBinaryWrapper(
            "ls", Path("/bin/ls"), BinaryType.SHARED_LIBRARY
        )
        self.assertIsNone(shared_lib_binary())


class TestTaggedCommits(unittest.TestCase):
    """Check if we can get a list of tagged commits from a project."""

    @classmethod
    def setUp(cls) -> None:
        """Initialize all projects before running tests."""
        initialize_projects()

    @staticmethod
    def hash_belongs_to_commit(hash_value: str) -> bool:
        return str(
            git("rev-parse", "--quiet", "--verify", hash_value).rstrip()
        ) == hash_value

    def test_get_tagged_commits_lightweight(self) -> None:
        """Check if we can get list of tagged commits from a project when
        lightweight tags are used."""
        fast_downward_tagged_commits = set(get_tagged_commits("fast_downward"))
        fast_downward_repo_loc = get_local_project_git_path("fast_downward")
        with local.cwd(fast_downward_repo_loc):
            for (hash_value, _) in fast_downward_tagged_commits:
                self.assertTrue(self.hash_belongs_to_commit(hash_value))

        # Assert tags are included (we cannot check for set equality since new
        # tags might be added in the repository)
        self.assertTrue(
            fast_downward_tagged_commits.issuperset({
                ('96ab3e3259af9c0a73d89b67a0549ea6b1736660', 'release-19.06.0'),
                ('fd21c6b0d070fcb8556db06fc65807e3f31389a6', 'release-19.12.0'),
                ('3a27ea77f85f41486c57286f5e73a5cac96cc35c', 'release-20.06.0'),
                ('e907baf9b847c28710873077b4670aa9e5310d57', 'release-21.12.0'),
                ('906f7fe0f7da35a0384576c07b2cf46ab6921269', 'release-22.06.0')
            })
        )

    def test_get_tagged_commits_annotated(self) -> None:
        """Check if we can get list of tagged commits from a project when
        annotated tags are used."""
        xz_tagged_commits = set(get_tagged_commits("xz"))
        xz_repo_loc = get_local_project_git_path("xz")
        with local.cwd(xz_repo_loc):
            for (hash_value, _) in xz_tagged_commits:
                self.assertTrue(self.hash_belongs_to_commit(hash_value))

        # Assert tags are included (we cannot check for set equality since new
        # tags might be added in the repository)
        self.assertTrue(
            xz_tagged_commits.issuperset({
                ('a0cd05ee71d330b79ead6eb9222e1b24e1559d3a', 'v5.2.0'),
                ('dec11497a71518423b5ff0e759100cf8aadf6c7b', 'v5.2.1'),
                ('9815cdf6987ef91a85493bfcfd1ce2aaf3b47a0a', 'v5.2.2'),
                ('3d566cd519017eee1a400e7961ff14058dfaf33c', 'v5.2.3'),
                ('b5be61cc06088bb07f488f9baf7d447ff47b37c1', 'v5.2.4'),
                ('2327a461e1afce862c22269b80d3517801103c1b', 'v5.2.5'),
                ('2267f5b0d20a5d24e93fcd9f72ea7eeb0d89708c', 'v5.3.1alpha'),
                ('edf525e2b1840dcaf377df472c67d8f11f8ace1b', 'v5.3.2alpha'),
            })
        )
