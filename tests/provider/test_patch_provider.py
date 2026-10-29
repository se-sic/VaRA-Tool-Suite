import unittest
from copy import deepcopy
from pathlib import Path
from shutil import copytree

import benchbuild as bb
from benchbuild.source.base import target_prefix
from plumbum import local

from tests.helper_utils import (
    TEST_INPUTS_DIR,
    UnitTestFixtures,
    run_in_test_environment,
)
from varats.projects.perf_tests.feature_perf_cs_collection import (
    FeaturePerfCSCollection,
)
from varats.provider.patch.patch_provider import Patch, PatchProvider, PatchSet
from varats.utils.git_util import (
    RepositoryHandle,
    ShortCommitHash,
    get_all_revisions_between,
    get_initial_commit,
)
from varats.utils.settings import bb_cfg, vara_cfg


class TestPatchProvider(unittest.TestCase):
    @staticmethod
    def _initialize_patch_repository(repository: Path) -> Path:
        """Initialize a copied patch-source fixture as a Git repository."""
        with local.cwd(repository):
            local["git"]("init")
            local["git"]("config", "user.email", "tests@example.com")
            local["git"]("config", "user.name", "Patch Provider Tests")
            local["git"]("add", ".")
            local["git"]("commit", "-m", "Add test patches")
        return repository

    @staticmethod
    def _create_patch_provider(
        repositories: list[Path], local_folders: list[str]
    ) -> PatchProvider:
        """Create a provider with the given Git and local patch sources."""
        vara_cfg()["patch_provider"]["repositories"] = [
            {
                "remote": str(repository),
                "local": repository.name,
                "refspec": "origin/HEAD",
            }
            for repository in repositories
        ]
        vara_cfg()["patch_provider"]["local_folders"] = local_folders
        return PatchProvider(FeaturePerfCSCollection)

    @run_in_test_environment(
        UnitTestFixtures.create_file_fixture(
            TEST_INPUTS_DIR / "patch_subdirectories",
            Path("patch_subdirectories"),
        ),
        UnitTestFixtures.create_project_repo_fixture(FeaturePerfCSCollection),
    )
    def test_reads_patches_from_two_git_sources(self) -> None:
        patch_repositories = [
            self._initialize_patch_repository(
                Path("patch_subdirectories") / source_name
            )
            for source_name in ["git_source_one", "git_source_two"]
        ]
        provider = self._create_patch_provider(patch_repositories, [])

        for shortname in ("git-source-one", "git-source-two"):
            self.assertIsNotNone(provider.get_by_shortname(shortname))

    @run_in_test_environment(
        UnitTestFixtures.create_file_fixture(
            TEST_INPUTS_DIR / "patch_subdirectories",
            Path("patch_subdirectories"),
        ),
        UnitTestFixtures.create_project_repo_fixture(FeaturePerfCSCollection),
    )
    def test_reads_patches_from_two_local_sources(self) -> None:
        provider = self._create_patch_provider(
            [],
            ["patch_subdirectories"],
        )

        for shortname in ("local-source-one", "local-source-two"):
            self.assertIsNotNone(provider.get_by_shortname(shortname))

    @run_in_test_environment(
        UnitTestFixtures.create_file_fixture(
            TEST_INPUTS_DIR / "patch_subdirectories",
            Path("patch_subdirectories"),
        ),
        UnitTestFixtures.create_project_repo_fixture(FeaturePerfCSCollection),
    )
    def test_reads_patches_from_local_repository_symlink(self) -> None:
        """Test that local repositories are linked into patch-sources."""
        local_folder = Path("patch_subdirectories")
        local_repository = local_folder / "local_source_one"
        vara_cfg()["patch_provider"]["repositories"] = []
        vara_cfg()["patch_provider"]["local_folders"] = [str(local_folder)]

        provider = PatchProvider(FeaturePerfCSCollection)

        repository_link = (
            Path(str(bb_cfg()["tmp_dir"]))
            / "patch-sources"
            / local_repository.name
        )
        self.assertTrue(repository_link.is_symlink())
        self.assertEqual(repository_link.resolve(), local_repository.resolve())
        self.assertIsNotNone(provider.get_by_shortname("local-source-one"))

    @run_in_test_environment(
        UnitTestFixtures.create_file_fixture(
            TEST_INPUTS_DIR / "patch_subdirectories",
            Path("patch_subdirectories"),
        ),
        UnitTestFixtures.create_project_repo_fixture(FeaturePerfCSCollection),
    )
    def test_reads_patches_from_git_and_local_source(self) -> None:
        repository = self._initialize_patch_repository(
            Path("patch_subdirectories/git_source_one")
        )
        local_folder = Path("local_patch_repositories")
        copytree(
            "patch_subdirectories/local_source_one",
            local_folder / "local_source_one",
        )
        provider = self._create_patch_provider(
            [repository],
            [str(local_folder)],
        )

        for shortname in ("git-source-one", "local-source-one"):
            self.assertIsNotNone(provider.get_by_shortname(shortname))

    def test_correct_patch_config_access(self) -> None:
        """Checks if we get a correct path for accessing the PatchConfig."""
        provider = PatchProvider.create_provider_for_project(
            FeaturePerfCSCollection
        )
        self.assertIsNotNone(provider)

    def test_get_patch_by_shortname(self) -> None:
        provider = PatchProvider.create_provider_for_project(
            FeaturePerfCSCollection
        )
        self.assertIsNotNone(provider)

        patch = provider.get_by_shortname("compile-error")
        self.assertIsNotNone(patch)

        patch = provider.get_by_shortname("dummy-patch")
        self.assertIsNone(patch)

    def test_parse_regression_severity(self) -> None:
        regression_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR
                / 'patch_configs/FeaturePerfCSCollection'
                / 'regression-severity.info'
            )
        )

        other_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR
                / 'patch_configs/FeaturePerfCSCollection'
                / 'unrestricted-range.info'
            )
        )

        self.assertIsNotNone(regression_patch.regression_severity)
        self.assertEqual(1000, regression_patch.regression_severity)
        self.assertIsNone(other_patch.regression_severity)


class TestPatchRevisionRanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patch_base_path = Path(
            TEST_INPUTS_DIR / 'patch_configs/FeaturePerfCSCollection/'
        )

        project_git_source = bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="FeaturePerfCSCollection",
            refspec="origin/HEAD",
            shallow=False,
        )

        project_git_source.fetch()

        repo = RepositoryHandle(
            Path(target_prefix() + "/FeaturePerfCSCollection")
        )

        cls.all_revisions = set(
            get_all_revisions_between(
                repo, get_initial_commit(repo).hash, "", ShortCommitHash
            )
        )

    def __test_patch_revisions(
        self, shortname: str, expected_revisions: set[ShortCommitHash]
    ) -> None:
        patch = Patch.from_yaml(self.patch_base_path / f"{shortname}.info")

        self.assertSetEqual(expected_revisions, patch.valid_revisions)

    def test_unrestricted_range(self) -> None:
        self.__test_patch_revisions("unrestricted-range", self.all_revisions)

    def test_include_single_revision(self) -> None:
        expected_revisions = {
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e")
        }

        self.__test_patch_revisions(
            "include-single-revision", expected_revisions
        )

    def test_include_revision_range(self) -> None:
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
        }

        self.__test_patch_revisions(
            "include-revision-range", expected_revisions
        )

    def test_included_single_and_revision_range(self) -> None:
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
            ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34"),
        }

        self.__test_patch_revisions(
            "include-single-and-revision-range", expected_revisions
        )

    def test_exclude_single_revision(self) -> None:
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.remove(
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e")
        )

        self.__test_patch_revisions(
            "exclude-single-revision", expected_revisions
        )

    def test_exclude_revision_range(self) -> None:
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.difference_update(
            {
                ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
                ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
                ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
                ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
                ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
            }
        )

        self.__test_patch_revisions(
            "exclude-revision-range", expected_revisions
        )

    def test_exclude_single_and_revision_range(self) -> None:
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.difference_update(
            {
                ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
                ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
                ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
                ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
                ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
                ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34"),
            }
        )

        self.__test_patch_revisions(
            "exclude-single-and-revision-range", expected_revisions
        )

    def test_include_range_exclude_single(self) -> None:
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
        }

        self.__test_patch_revisions(
            "include-range-exclude-single", expected_revisions
        )

    def test_include_range_exclude_range(self) -> None:
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("4300ea495e7f013f68e785fdde5c4ead81297999"),
            ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34"),
            ShortCommitHash("32b28ee90e2475cf44d7a616101bcaba2396168d"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
        }

        self.__test_patch_revisions(
            "include-range-exclude-range", expected_revisions
        )


class TestPatchSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        patches = {
            Patch(
                "TEST",
                "Test-ABCD",
                "",
                path=Path("test.patch"),
                tags={"A", "B", "C", "D"},
                feature_tags={"F_A", "F_B", "F_C", "F_D"},
            ),
            Patch(
                "TEST",
                "Test-A",
                "",
                path=Path("test.patch"),
                tags={"A"},
                feature_tags={"F_A"},
            ),
            Patch(
                "TEST",
                "Test-B",
                "",
                path=Path("test.patch"),
                tags={"B"},
                feature_tags={"F_B"},
            ),
            Patch(
                "TEST",
                "Test-C",
                "",
                path=Path("test.patch"),
                tags={"C"},
                feature_tags={"F_C"},
            ),
            Patch(
                "TEST",
                "Test-D",
                "",
                path=Path("test.patch"),
                tags={"D"},
                feature_tags={"F_D"},
            ),
            Patch(
                "TEST",
                "Test-AB",
                "",
                path=Path("test.patch"),
                tags={"A", "B"},
                feature_tags={"F_A", "F_B"},
            ),
            Patch(
                "TEST",
                "Test-AC",
                "",
                path=Path("test.patch"),
                tags={"A", "C"},
                feature_tags={"F_A", "F_C"},
            ),
            Patch(
                "TEST",
                "Test-AD",
                "",
                path=Path("test.patch"),
                tags={"A", "D"},
                feature_tags={"F_A", "F_D"},
            ),
            Patch(
                "TEST",
                "Test-BC",
                "",
                path=Path("test.patch"),
                tags={"B", "C"},
                feature_tags={"F_B", "F_C"},
            ),
            Patch(
                "TEST",
                "Test-BD",
                "",
                path=Path("test.patch"),
                tags={"B", "D"},
                feature_tags={"F_B", "F_D"},
            ),
            Patch(
                "TEST",
                "Test-CD",
                "",
                path=Path("test.patch"),
                tags={"C", "D"},
                feature_tags={"F_C", "F_D"},
            ),
            Patch(
                "TEST",
                "Test-ABC",
                "",
                path=Path("test.patch"),
                tags={"A", "B", "C"},
                feature_tags={"F_A", "F_B", "F_C"},
            ),
            Patch(
                "TEST",
                "Test-ABD",
                "",
                path=Path("test.patch"),
                tags={"A", "B", "D"},
                feature_tags={"F_A", "F_B", "F_D"},
            ),
            Patch(
                "TEST",
                "Test-ACD",
                "",
                path=Path("test.patch"),
                tags={"A", "C", "D"},
                feature_tags={"F_A", "F_C", "F_D"},
            ),
            Patch(
                "TEST",
                "Test-BCD",
                "",
                path=Path("test.patch"),
                tags={"B", "C", "D"},
                feature_tags={"F_B", "F_C", "F_D"},
            ),
        }

        cls.patchSet = PatchSet(patches)

    def test_bracket_single_tag(self) -> None:
        for tag in ("A", "B", "C", "D"):
            patches = self.patchSet[tag]
            self.assertEqual(8, len(patches))

            for patch in patches:
                self.assertIn(tag, patch.shortname)

    def test_bracket_multiple_tags(self) -> None:
        tags_count = {
            ("A", "B"): 4,
            ("C", "B"): 4,
            ("D", "B"): 4,
            ("A", "B", "C"): 2,
            ("A", "B", "C", "D"): 1,
        }

        for tags, value in tags_count.items():
            patches = self.patchSet[tags]

            self.assertEqual(value, len(patches))

            for patch in patches:
                for tag in tags:
                    self.assertIn(tag, patch.tags)

    def test_all_of_single_tag(self) -> None:
        for tag in ("A", "B", "C", "D"):
            patches = self.patchSet.all_of(tag)
            self.assertEqual(8, len(patches))

            for patch in patches:
                self.assertIn(tag, patch.shortname)

    def test_all_of_multiple_tags(self) -> None:
        tags_count = {
            ("A", "B"): 4,
            ("C", "B"): 4,
            ("D", "B"): 4,
            ("A", "B", "C"): 2,
            ("A", "B", "C", "D"): 1,
        }

        for tags, value in tags_count.items():
            patches = self.patchSet.all_of(tags)

            self.assertEqual(value, len(patches))

            for patch in patches:
                for tag in tags:
                    self.assertIn(tag, patch.tags)

    def test_any_of_single_tag(self) -> None:
        for tag in ("A", "B", "C", "D"):
            patches = self.patchSet.any_of(tag)
            self.assertEqual(8, len(patches))

            for patch in patches:
                self.assertIn(tag, patch.shortname)

    def test_any_of_multiple_tags(self) -> None:
        tags_count = {
            ("A", "B"): 12,
            ("C", "B"): 12,
            ("D", "B"): 12,
            ("A", "B", "C"): 14,
            ("A", "B", "C", "D"): 15,
        }

        for tags, value in tags_count.items():
            patches = self.patchSet.any_of(tags)

            self.assertEqual(value, len(patches))

            for patch in patches:
                self.assertTrue(any(tag in patch.tags for tag in tags))

    def test_all_of_single_feature_tag(self) -> None:
        for tag in ("F_A", "F_B", "F_C", "F_D"):
            patches = self.patchSet.all_of_features([tag])
            self.assertEqual(8, len(patches))

    def test_all_of_multiple_feature_tags(self) -> None:
        tags_count = {
            ("F_A", "F_B"): 4,
            ("F_C", "F_B"): 4,
            ("F_D", "F_B"): 4,
            ("F_A", "F_B", "F_C"): 2,
            ("F_A", "F_B", "F_C", "F_D"): 1,
        }

        for tags, value in tags_count.items():
            patches = self.patchSet.all_of_features(tags)
            self.assertEqual(value, len(patches))

    def test_any_of_single_feature_tag(self) -> None:
        for tag in ("F_A", "F_B", "F_C", "F_D"):
            patches = self.patchSet.any_of_features([tag])
            self.assertEqual(8, len(patches))

    def test_any_of_multiple_feature_tags(self) -> None:
        tags_count = {
            ("F_A", "F_B"): 12,
            ("F_C", "F_B"): 12,
            ("F_D", "F_B"): 12,
            ("F_A", "F_B", "F_C"): 14,
            ("F_A", "F_B", "F_C", "F_D"): 15,
        }

        for tags, value in tags_count.items():
            patches = self.patchSet.any_of_features(tags)
            self.assertEqual(value, len(patches))

    def test_patchset_intersection(self) -> None:
        patches = self.patchSet["A"] & self.patchSet["B"]

        self.assertEqual(4, len(patches))

        patches = patches & self.patchSet["C"]
        self.assertEqual(2, len(patches))

        patches = patches & self.patchSet["D"]
        self.assertEqual(1, len(patches))

    def test_patchset_union(self) -> None:
        patches = self.patchSet["A"] | self.patchSet["B"]

        self.assertEqual(12, len(patches))

        patches = patches | self.patchSet["C"]
        self.assertEqual(14, len(patches))

        patches = patches | self.patchSet["D"]
        self.assertEqual(15, len(patches))
