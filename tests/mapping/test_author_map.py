import unittest

from varats.mapping.author_map import generate_author_map, Author, AuthorMap
from varats.projects.discover_projects import initialize_projects


class TestAuthor(unittest.TestCase):

    def test_merge(self) -> None:
        author_one = Author(1, "Jon Doe", "jon_doe@jon_doe.com")
        author_two = Author(4, "J. Doe", "jon_doe@jon_doe.com")
        author_three = Author(2, "Jon Doe", "j_doe@gmail.com")
        merge_one = author_one.merge(author_two)
        merge_two = author_three.merge(author_one)
        self.assertEqual(merge_one.author_id, 1)
        self.assertEqual(merge_one.names, {"Jon Doe", "J. Doe"})
        self.assertEqual(merge_one.mail_addresses, {"jon_doe@jon_doe.com"})
        self.assertEqual(merge_two.author_id, 1)
        self.assertEqual(merge_two.names, {"Jon Doe", "J. Doe"})
        self.assertEqual(
            merge_two.mail_addresses,
            {"jon_doe@jon_doe.com", "j_doe@gmail.com"}
        )


class TestAuthorMap(unittest.TestCase):

    def test_get_author_by_email(self) -> None:
        initialize_projects()
        amap = generate_author_map("xz")
        test_author = amap.get_author_by_email("jim@meyering.net")
        self.assertEqual(
            test_author.mail_addresses,
            {"meyering@redhat.com", "jim@meyering.net"}
        )
        self.assertEqual(test_author.names, {"Jim Meyering"})

    def test_get_author_by_name(self) -> None:
        initialize_projects()
        amap = generate_author_map("xz")
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
        amap = generate_author_map("xz")
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
        amap = generate_author_map("xz")
        self.assertIsNone(amap.get_author("Jia Cheong Tan", "jim@meyering.net"))

    def test_get_author_missing_mail(self) -> None:
        initialize_projects()
        amap = generate_author_map("xz")
        self.assertIsNone(
            amap.get_author("Jia Cheong Tan", "notpresent@None.com")
        )

    def test_get_author_missing_name(self) -> None:
        initialize_projects()
        amap = generate_author_map("xz")
        self.assertIsNone(amap.get_author("Not Present", "jim@meyering.net"))

    def test_get_author_missing(self) -> None:
        initialize_projects()
        amap = generate_author_map("xz")
        self.assertIsNone(amap.get_author("Not Present", "notpresent@None.com"))

    def test_author_merging(self) -> None:
        amap = AuthorMap()
        amap.add_entry("Jon Doe", "jon_doe@jon_doe.com")
        amap.add_entry("JD", "jon.d@gmail.com")
        amap.add_entry("Jon Doe", "jon.d@gmail.com")
        disambiguated_author = amap.get_author("JD", "jon_doe@jon_doe.com")
        self.assertEqual(disambiguated_author.author_id, 0)
        self.assertEqual(disambiguated_author.names, {"Jon Doe", "JD"})
        self.assertEqual(
            disambiguated_author.mail_addresses,
            {"jon_doe@jon_doe.com", "jon.d@gmail.com"}
        )

    def test_author_merging_generate(self) -> None:
        initialize_projects()
        amap = generate_author_map("brotli")
        test_author = amap.get_author("eustas", "eustas@google.com")
        self.assertEqual(
            test_author.names, {
                "eustas", "Eugene Kliuchnikov", "Eugene Klyuchnikov",
                "Evgenii Kliuchnikov"
            }
        )
        self.assertEqual(
            test_author.mail_addresses, {
                "eustas@google.com", "eustas.ru@gmail.com",
                "eustas@eustas-wfh.fra.corp.google.com"
            }
        )
