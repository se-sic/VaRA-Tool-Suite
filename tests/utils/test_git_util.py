"""Test VaRA git utilities."""
import unittest

from varats.utils.git_util import ChurnConfig


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
        self.assertEqual(c_config.get_extensions_repr(), "c, h")
        self.assertEqual(c_config.get_extensions_repr("|"), "c|h")

        c_style_config = ChurnConfig.create_c_style_languages_config()
        self.assertEqual(
            c_style_config.get_extensions_repr(), "c, cpp, cxx, h, hpp, hxx"
        )
        self.assertEqual(
            c_style_config.get_extensions_repr("|"), "c|cpp|cxx|h|hpp|hxx"
        )
