import unittest
from copy import deepcopy
from pathlib import Path

import benchbuild as bb
from benchbuild.source.base import target_prefix
from benchbuild.utils.revision_ranges import _get_git_for_path

from tests.helper_utils import TEST_INPUTS_DIR
from varats.projects.perf_tests.feature_perf_cs_collection import (
    FeaturePerfCSCollection,
)
from varats.provider.patch.patch_provider import PatchProvider, Patch
from varats.utils.git_util import ShortCommitHash


class TestPatchProvider(unittest.TestCase):

    def test_correct_patch_config_access(self):
        """Checks if we get a correct path for accessing the PatchConfig."""
        provider = PatchProvider.create_provider_for_project(
            FeaturePerfCSCollection
        )
        self.assertIsNotNone(provider)

    def test_get_patch_by_shortname(self):
        provider = PatchProvider.create_provider_for_project(
            FeaturePerfCSCollection
        )
        self.assertIsNotNone(provider)

        patch = provider.get_by_shortname("patch-10")
        self.assertIsNotNone(patch)

        patch = provider.get_by_shortname("dummy-patch")
        self.assertIsNone(patch)


class TestPatchRevisionRanges(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.patch_base_path = Path(
            TEST_INPUTS_DIR / 'patch_configs/FeaturePerfCSCollection/'
        )

        project_git_source = bb.source.Git(
            remote="git@github.com:se-sic/FeaturePerfCSCollection.git",
            local="FeaturePerfCSCollection",
            refspec="origin/HEAD",
            shallow=False,
        )

        project_git_source.fetch()

        repo_git = _get_git_for_path(
            target_prefix() + "/FeaturePerfCSCollection"
        )

        cls.all_revisions = {
            ShortCommitHash(h) for h in
            repo_git('log', '--pretty=%H', '--first-parent').strip().split()
        }

    def __test_patch_revisions(
        self, shortname: str, expected_revisions: set[ShortCommitHash]
    ):
        patch = Patch.from_yaml(self.patch_base_path / f"{shortname}.info")

        self.assertSetEqual(expected_revisions, patch.valid_revisions)

    def test_unrestricted_range(self):
        self.__test_patch_revisions("unrestricted-range", self.all_revisions)

    def test_include_single_revision(self):
        expected_revisions = {
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e")
        }

        self.__test_patch_revisions(
            "include-single-revision", expected_revisions
        )

    def test_include_revision_range(self):
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9")
        }

        self.__test_patch_revisions(
            "include-revision-range", expected_revisions
        )

    def test_included_single_and_revision_range(self):
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
            ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34")
        }

        self.__test_patch_revisions(
            "include-single-and-revision-range", expected_revisions
        )

    def test_exclude_single_revision(self):
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.remove(
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e")
        )

        self.__test_patch_revisions(
            "exclude-single-revision", expected_revisions
        )

    def test_exclude_revision_range(self):
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.difference_update({
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9")
        })

        self.__test_patch_revisions(
            "exclude-revision-range", expected_revisions
        )

    def test_exclude_single_and_revision_range(self):
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.difference_update({
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
            ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34")
        })

        self.__test_patch_revisions(
            "exclude-single-and-revision-range", expected_revisions
        )

    def test_include_range_exclude_single(self):
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9")
        }

        self.__test_patch_revisions(
            "include-range-exclude-single", expected_revisions
        )

    def test_include_range_exclude_range(self):
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("4300ea495e7f013f68e785fdde5c4ead81297999"),
            ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34"),
            ShortCommitHash("32b28ee90e2475cf44d7a616101bcaba2396168d"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9")
        }

        self.__test_patch_revisions(
            "include-range-exclude-range", expected_revisions
        )
