import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import NamedTemporaryFile

from varats.mapping.author_map import generate_author_map, Author
from varats.project.project_util import get_local_project_git_path
from varats.projects.discover_projects import initialize_projects


class TestAuthorMap(unittest.TestCase):

    def test_get_author_by_email(self):
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        self.assertEqual(
            amap.get_author_by_email("jim@meyering.net"),
            Author(19, "Jim Meyering", "meyering@redhat.com")
        )

    def test_get_author_by_email(self):
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        self.assertEqual(
            amap.get_author_by_name("Jia Cheong Tan"),
            Author(1, "Jia  Tan", "jiat0218@gmail.com")
        )
