import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import NamedTemporaryFile

from varats.mapping.author_map import generate_author_map, Author
from varats.project.project_util import get_local_project_git_path
from varats.projects.discover_projects import initialize_projects


class TestAuthorMap(unittest.TestCase):

    def test_get_author_by_email(self) -> None:
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        test_author = amap.get_author_by_email("jim@meyering.net")
        self.assertEqual(
            test_author.mail_addresses,
            {"meyering@redhat.com", "jim@meyering.net"}
        )
        self.assertEqual(test_author.names, {"Jim Meyering"})

    def test_get_author_by_name(self) -> None:
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        test_author = amap.get_author_by_name("Jia Cheong Tan")
        self.assertEqual(
            test_author.names, {"Jia Cheong Tan", "Jia Tan", "jiat75"}
        )
        self.assertEqual(
            test_author.mail_addresses,
            {"jiat0218@gmail.com", "jiat75@gmail.com"}
        )

    def test_get_author(self) -> None:
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        test_author = amap.get_author("Jia Cheong Tan", "jiat75@gmail.com")
        self.assertEqual(
            test_author.names, {"Jia Cheong Tan", "Jia Tan", "jiat75"}
        )
        self.assertEqual(
            test_author.mail_addresses,
            {"jiat0218@gmail.com", "jiat75@gmail.com"}
        )

    def test_get_author_ambiguous(self) -> None:
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        self.assertIsNone(amap.get_author("Jia Cheong Tan", "jim@meyering.net"))

    def test_get_author_missing_mail(self) -> None:
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        self.assertIsNone(
            amap.get_author("Jia Cheong Tan", "notpresent@None.com")
        )

    def test_get_author_missing_name(self) -> None:
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        self.assertIsNone(amap.get_author("Not Present", "jim@meyering.net"))

    def test_get_author_missing(self) -> None:
        initialize_projects()
        git_path = get_local_project_git_path("xz")
        amap = generate_author_map(git_path)
        self.assertIsNone(amap.get_author("Not Present", "notpresent@None.com"))
