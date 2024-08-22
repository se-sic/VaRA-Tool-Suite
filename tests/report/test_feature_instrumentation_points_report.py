from unittest import TestCase

from tests.helper_utils import TEST_INPUTS_DIR
from varats.data.reports.feature_instrumentation_points_report import (
    FeatureInstrumentationPointsReport,
)


class TestFeatureInstrumentationPointsReport(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__report = FeatureInstrumentationPointsReport(
            TEST_INPUTS_DIR /
            "results/WorkloadFeatureInteraction/FIP-FIP-WorkloadFeatureIntensity-WorkloadFeatureIntensity-1e40d95903/b48b4216-b54c-42f6-8206-0d19d23ec628_config-0_success.txt"
        )

        cls.__feature_regions = {
            "A": {
                1729382256910303235,
                1729382256910434307,
                1729382256910483459,
            },
            "B": {
                1729382256910516227, 1729382256910499843, 1729382256910368771,
                1729382256910270467, 1729382256910450691
            },
            "C": {
                1729382256910565379,
                1729382256910532611,
                1729382256910401539,
                1729382256910352387,
                1729382256910286851,
            },
            "D": {
                1729382256910548995, 1729382256910385155, 1729382256910336003,
                1729382256910319619, 1729382256910417923, 1729382256910467075
            }
        }
        pass

    def test_uuid_parsing(self):
        expected_region_uuids = {
            uuid for feature_regions in self.__feature_regions.values()
            for uuid in feature_regions
        }

        self.assertEqual(
            len(expected_region_uuids), len(self.__report.feature_regions())
        )
        self.assertSetEqual(
            expected_region_uuids, self.__report.feature_regions()
        )

    def test_feature_name_parsing(self):
        expected_names = set(self.__feature_regions.keys())

        self.assertEqual(
            len(expected_names), len(self.__report.feature_names())
        )
        self.assertSetEqual(expected_names, self.__report.feature_names())

    def test_feature_regions_mapping(self):
        for feature_name in self.__feature_regions:
            self.assertEqual(
                len(self.__feature_regions[feature_name]),
                len(self.__report.regions_for_feature(feature_name))
            )
            self.assertSetEqual(
                self.__feature_regions[feature_name],
                self.__report.regions_for_feature(feature_name)
            )

    def test_feature_names_mapping(self):
        for feature_name in self.__feature_regions:
            for region_uuid in self.__feature_regions[feature_name]:
                self.assertEqual(
                    feature_name,
                    self.__report.feature_name_for_region(region_uuid)
                )
