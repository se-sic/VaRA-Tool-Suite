import unittest
from pathlib import Path

from tests.helper_utils import TEST_INPUTS_DIR
from varats.provider.patch.patch import ProjectPatches


class TestPatchProvider(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, True)


class TestPatchConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patch_config = ProjectPatches.from_xml( Path(TEST_INPUTS_DIR/'patch-configs/test-patch-configuration.xml') )

    def test_unrestricted_range(self):
        pass

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
