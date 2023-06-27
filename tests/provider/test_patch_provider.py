import unittest
from pathlib import Path

import benchbuild as bb
from benchbuild.source.base import target_prefix
from benchbuild.utils.revision_ranges import _get_git_for_path

from tests.helper_utils import TEST_INPUTS_DIR
from varats.provider.patch.patch_provider import ProjectPatchesConfiguration

from varats.project.project_util import get_local_project_git_path
from varats.utils.git_util import ShortCommitHash


class TestPatchProvider(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, True)


class TestPatchConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        patch_config = ProjectPatchesConfiguration.from_xml(Path(TEST_INPUTS_DIR / 'patch-configs/FeaturePerfCSCollection/test-patch-configuration.xml'))
        cls.patch_config = patch_config

        project_git_source = bb.source.Git(
            remote="git@github.com:se-sic/FeaturePerfCSCollection.git",
            local="FeaturePerfCSCollection",
            refspec="origin/HEAD",
            shallow=False,
        )

        project_git_source.fetch()

        repo_git = _get_git_for_path(target_prefix() + "/FeaturePerfCSCollection")

        cls.all_revisions = { ShortCommitHash(h) for h in repo_git('log', '--pretty=%H', '--first-parent').strip().split() }

    def test_unrestricted_range(self):
        patch = self.patch_config.get_by_shortname('unrestricted-range')

        self.assertEqual(patch.valid_revisions, set(self.all_revisions))

    def test_included_single_revision(self):
        pass

    def test_included_revision_range(self):
        pass

    def test_included_single_and_revision_range(self):
        pass

    def test_exclude_single_revision(self):
        pass

    def test_exclude_revision_range(self):
        pass

    def test_exclude_single_and_revision_range(self):
        pass

    def test_include_range_exclude_single(self):
        pass

    def test_include_range_exclude_range(self):
        pass
