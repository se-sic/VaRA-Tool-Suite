import unittest

from pygit2 import Walker
from pygit2.enums import SortMode

from varats.project.project_util import get_local_project_repo
from varats.ts_utils.feature_util import Location


class TestFeatureUtils(unittest.TestCase):

    @classmethod
    def get_pygit_commit(cls, project: str, revision=None):
        """Mock method to return a commit object."""
        repo = get_local_project_repo(project).pygit_repo
        walker: Walker

        walker = repo.walk(
            repo.head.target, SortMode.TOPOLOGICAL | SortMode.REVERSE
        )
        walker.simplify_first_parent()

        first_commit = next(walker)
        commit = repo.get(revision)
        while first_commit != commit:
            first_commit = next(walker)

    def test_parse_location(self):
        test_location = Location.parse_string("file.py 10:20 12:15")
        self.assertEqual(test_location.file, "file.py")
        self.assertEqual(test_location.start_line, 10)
        self.assertEqual(test_location.start_col, 20)
        self.assertEqual(test_location.end_line, 12)
        self.assertEqual(test_location.end_col, 15)
        test_location = Location.parse_string("12", test_location)
        self.assertEqual(test_location.file, "file.py")
        self.assertEqual(test_location.start_line, 12)
        self.assertEqual(test_location.start_col, 20)
        self.assertEqual(test_location.end_line, 14)
        self.assertEqual(test_location.end_col, 15)
        test_location = Location.parse_string("file.py 10:20")
        self.assertEqual(test_location.file, "file.py")
        self.assertEqual(test_location.start_line, 10)
        self.assertEqual(test_location.start_col, 20)
        self.assertEqual(test_location.end_line, 10)
        self.assertEqual(test_location.end_col, None)
