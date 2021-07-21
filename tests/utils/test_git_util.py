"""Test VaRA git utilities."""
import unittest

from varats.utils.git_util import ChurnConfig, CommitRepoPair, FullCommitHash


class TestChurnConfig(unittest.TestCase):
    """Test if ChurnConfig sets languages correctly."""

    def test_enable_language(self):
        init_config = ChurnConfig.create_default_config()
        self.assertFalse(init_config.is_enabled('c'))
        init_config.enable_language(ChurnConfig.Language.CPP)
        self.assertFalse(init_config.is_enabled('c'))
        init_config.enable_language(ChurnConfig.Language.C)
        self.assertTrue(init_config.is_enabled('c'))

    def test_initial_config(self):
        init_config = ChurnConfig.create_default_config()
        self.assertTrue(init_config.include_everything)
        self.assertListEqual(init_config.enabled_languages, [])

    def test_c_language_config(self):
        c_style_config = ChurnConfig.create_c_language_config()
        self.assertTrue(c_style_config.is_enabled('h'))
        self.assertTrue(c_style_config.is_enabled('c'))

    def test_c_style_config(self):
        c_style_config = ChurnConfig.create_c_style_languages_config()
        self.assertTrue(c_style_config.is_enabled('h'))
        self.assertTrue(c_style_config.is_enabled('c'))
        self.assertTrue(c_style_config.is_enabled('hpp'))
        self.assertTrue(c_style_config.is_enabled('cpp'))
        self.assertTrue(c_style_config.is_enabled('hxx'))
        self.assertTrue(c_style_config.is_enabled('cxx'))

    def test_enabled_language(self):
        c_config = ChurnConfig.create_c_language_config()
        self.assertTrue(c_config.is_language_enabled(ChurnConfig.Language.C))
        self.assertFalse(c_config.is_language_enabled(ChurnConfig.Language.CPP))

    def test_extensions_repr_gen(self):
        c_config = ChurnConfig.create_c_language_config()
        self.assertEqual(c_config.get_extensions_repr(), ["c", "h"])
        self.assertEqual(
            c_config.get_extensions_repr(prefix="*."), ["*.c", "*.h"]
        )
        self.assertEqual(c_config.get_extensions_repr(suffix="|"), ["c|", "h|"])

        c_style_config = ChurnConfig.create_c_style_languages_config()
        self.assertEqual(
            c_style_config.get_extensions_repr(),
            ["c", "cpp", "cxx", "h", "hpp", "hxx"]
        )
        self.assertEqual(
            c_style_config.get_extensions_repr(prefix="*."),
            ["*.c", "*.cpp", "*.cxx", "*.h", "*.hpp", "*.hxx"]
        )
        self.assertEqual(
            c_style_config.get_extensions_repr(suffix="|"),
            ["c|", "cpp|", "cxx|", "h|", "hpp|", "hxx|"]
        )


class TestCommitRepoPair(unittest.TestCase):
    """Test driver for the CommitRepoPair class."""

    @classmethod
    def setUpClass(cls):
        cls.cr_pair = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

    def test_commit_hash(self):
        self.assertEqual(
            self.cr_pair.commit_hash,
            FullCommitHash("4200000000000000000000000000000000000000")
        )

    def test_repo_name(self):
        self.assertEqual(self.cr_pair.repository_name, "foo_repo")

    def test_less_equal(self):
        """Tests that two equal pairs are not less."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertFalse(cr_pair_1 < cr_pair_2)

    def test_less_commit(self):
        """Tests that a smaller commit is less."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4100000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertTrue(cr_pair_1 < cr_pair_2)

    def test_less_repo(self):
        """Tests that a smaller repo is less, if the commits are equal."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "boo_repo"
        )

        self.assertFalse(cr_pair_1 < cr_pair_2)

    def tests_less_something_other(self):
        self.assertFalse(self.cr_pair < 42)

    def test_equal_equal(self):
        """Tests that two equal pairs are equal."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertTrue(cr_pair_1 == cr_pair_2)

    def test_equal_commit(self):
        """Tests that two different commits are not equal."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4100000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertFalse(cr_pair_1 == cr_pair_2)

    def test_equal_repo(self):
        """Tests that two different commits are not equal."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "bar_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertFalse(cr_pair_1 == cr_pair_2)

    def tests_equal_something_other(self):
        self.assertFalse(self.cr_pair == 42)

    def test_to_string(self):
        self.assertEqual(
            str(self.cr_pair),
            "foo_repo[4200000000000000000000000000000000000000]"
        )
