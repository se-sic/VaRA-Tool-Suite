"""Tests for feature_model_provider."""
import unittest
from unittest.mock import create_autospec

from tests.utils.test_experiment_util import BBTestProject
from varats.projects.c_projects.x264 import X264
from varats.provider.feature.feature_model_provider import FeatureModelProvider


class TestFeatureModelProvider(unittest.TestCase):
    """Test if the FeatureModelProvider can access and provide paths to
    FeatureModels."""

    def test_correct_feature_model_path_access(self):
        """Checks if we get a correct path for accessing the FeatureModel."""
        provider = FeatureModelProvider.create_provider_for_project(X264)
        self.assertIsNotNone(provider)
        if provider:
            self.assertTrue(
                str(provider.get_feature_model_path("dummy_revision")
                   ).endswith("ConfigurableSystems/x264/FeatureModel.xml")
            )

    def test_false_feature_model_path_access(self):
        """Checks look-up for none existens FeatureModels."""
        provider = FeatureModelProvider.create_provider_for_project(
            BBTestProject
        )
        self.assertIsNotNone(provider)
        if provider:
            self.assertIsNone(provider.get_feature_model_path("dummy_revision"))
