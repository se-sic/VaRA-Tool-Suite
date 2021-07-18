"""Test module for ConfigurationOption tests."""

import unittest

import varats.base.commandline_option as CO
from tests.test_utils import ConfigurationHelper
from varats.base.configuration import Configuration, ConfigurationImpl


class TestCommandlineOptionSwitch(unittest.TestCase):
    """Test if CommandlineOptionSwitch is working."""

    @classmethod
    def setUpClass(cls):
        """Setup test Configuration."""
        cls.test_config = ConfigurationHelper.create_test_config()

    def test_alias(self):
        self.assertEqual(CO.CommandlineOptionSwitch, CO.CLOSwitch)

    def test_render_simple_true_flag(self):
        """Test if OptionSwitch renders a simple flag correctly."""
        option_flag = "--flag"
        option = CO.CLOSwitch("foo", option_flag)

        self.assertEqual(option_flag, option.render(self.test_config))

    def test_render_simple_false_flag(self):
        """Test if OptionSwitch does not render a the flag when the option is
        False."""
        option_flag = "--flag"
        option = CO.CLOSwitch("bar", option_flag)

        self.assertEqual("", option.render(self.test_config))

    def test_render_missing_flag(self):
        """Test if OptionSwitch does not render a flag when the option is
        missing."""
        option_flag = "--flag"
        option = CO.CLOSwitch("missing", option_flag)

        self.assertEqual("", option.render(self.test_config))

    def test_render_value_flag(self):
        """Test if OptionSwitch does render a the flag when the options value is
        convertable to True."""
        option_flag = "--flag"
        option = CO.CLOSwitch("bazz", option_flag)

        self.assertEqual(option_flag, option.render(self.test_config))

    def test_render_false_flag_own_condition(self):
        """Test if OptionSwitch does render a the flag when the option is False
        but a condition override was used."""
        option_flag = "--flag"
        option = CO.CLOSwitch("bar", option_flag, False)

        self.assertEqual(option_flag, option.render(self.test_config))


class TestCommandlineOptionFormat(unittest.TestCase):
    """Test if CommandlineOptionFormat is working."""

    @classmethod
    def setUpClass(cls):
        """Setup test Configuration."""
        cls.test_config = ConfigurationHelper.create_test_config()

    def test_alias(self):
        self.assertEqual(CO.CommandlineOptionFormat, CO.CLOFormat)

    def test_render_flag(self):
        """Test if OptionFormat renders a flag correctly."""
        option_flag = "--{bazz}"
        option = CO.CLOFormat("bazz", option_flag)

        self.assertEqual("--bazz-value", option.render(self.test_config))

    def test_render_true_flag(self):
        """Test if OptionSwitch renders a bool flag correctly by injecting the
        value and converting it to a string."""
        option_flag = "--enable-fooer={foo}"
        option = CO.CLOFormat("foo", option_flag)

        self.assertEqual("--enable-fooer=True", option.render(self.test_config))

    def test_render_false_flag_own_condition(self):
        """Test if OptionFormat does not render a flag when a special condition
        is not fullfilled."""

        def dont_enable_if_foo_is_true(config: Configuration) -> bool:
            maybe_value = config.get_config_value("foo")
            if maybe_value is not None and bool(maybe_value.value):
                return False

            return True

        option_flag = "--{bazz}"
        option = CO.CLOFormat("bazz", option_flag, dont_enable_if_foo_is_true)

        self.assertEqual("", option.render(self.test_config))


class TestCommandlineOptionGroup(unittest.TestCase):
    """Test if CommandlineOptionGroup is working."""

    @classmethod
    def setUpClass(cls):
        """Setup test Configuration."""
        cls.test_config = ConfigurationHelper.create_test_config()

    def test_alias(self):
        self.assertEqual(CO.CommandlineOptionGroup, CO.CLOGroup)

    def test_two_flags_in_order(self):
        """Checks of two flags in a group get printed in order."""
        option_flag_1 = "--flag"
        option_flag_2 = "--flag2"
        option = CO.CLOGroup([
            CO.CLOSwitch("foo", option_flag_1),
            CO.CLOSwitch("bazz", option_flag_2)
        ])

        self.assertEqual(
            option_flag_1 + " " + option_flag_2,
            option.render(self.test_config)
        )
