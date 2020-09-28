"""Test module for sampling method tests."""

import unittest

from varats.base.sampling_method import NormalSamplingMethod


class TestNormalSamplingMethod(unittest.TestCase):
    """Test if NormalSamplingMethod is working."""

    def test_if_all_sampling_methods_are_detected(self) -> None:
        """Checks of the automatic registration of NormalSamplingMethod
        works."""
        print(NormalSamplingMethod.normal_sampling_method_types())
        self.assertEqual(
            len(NormalSamplingMethod.normal_sampling_method_types()), 2
        )
