"""Test module for sampling method tests."""

import typing as tp
import unittest

from varats.base.sampling_method import (
    NormalSamplingMethod,
    SamplingMethodBase,
    UniformSamplingMethod,
)


class TestSamplingMethodBase(unittest.TestCase):
    """Test if SamplingMethodBase is working."""

    def test_registering_new_sampling_methods(self) -> None:
        """Tests if new sampling classes get automatically added to the
        registry."""
        self.assertFalse(
            'NewTestSamplingMethod' in SamplingMethodBase[
                tp.Any].sampling_method_names()
        )

        class NewTestSamplingMethod(SamplingMethodBase):  # pylint: disable=W0612
            pass

        self.assertTrue(
            'NewTestSamplingMethod' in SamplingMethodBase[
                tp.Any].sampling_method_names()
        )

    def test_sampling_method_lookup(self) -> None:
        """Test if the type look-up for sampling methods works."""
        self.assertEqual(
            SamplingMethodBase.
            get_sampling_method_type("UniformSamplingMethod"),
            UniformSamplingMethod
        )

    def test_dump_sampling_method(self) -> None:
        """Test if we can dump the sampling method configuration into a
        string."""
        expected_usm_dump = "{'sampling_method': 'UniformSamplingMethod'}"
        self.assertEqual(
            UniformSamplingMethod().dump_to_string(), expected_usm_dump
        )

    def test_create_sampling_method_from_string(self) -> None:
        """Test if we can reload the sampling method from a configuration and
        create the correct type."""
        dumped_usm = "{'sampling_method': 'UniformSamplingMethod'}"
        self.assertEqual(
            type(
                SamplingMethodBase[
                    tp.Any].create_sampling_method_from_config_str(dumped_usm)
            ), UniformSamplingMethod
        )


class TestNormalSamplingMethod(unittest.TestCase):
    """Test if NormalSamplingMethod is working."""

    def test_if_all_sampling_methods_are_detected(self) -> None:
        """Checks of the automatic registration of NormalSamplingMethod
        works."""
        print(NormalSamplingMethod.normal_sampling_method_types())
        self.assertEqual(
            len(NormalSamplingMethod.normal_sampling_method_types()), 2
        )
