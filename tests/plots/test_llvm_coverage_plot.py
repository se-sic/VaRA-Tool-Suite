import unittest
from unittest.mock import create_autospec

from varats.base.configuration import PlainCommandlineConfiguration
from varats.data.reports.llvm_coverage_report import CodeRegion, CoverageReport
from varats.varats.plots.llvm_coverage_plot import ConfigCoverageReportMapping

CODE_REGION_1 = CodeRegion.from_list([9, 79, 17, 2, 4, 0, 0, 0], "main")


class TestCodeRegion(unittest.TestCase):

    def test_feature_config_report_map(self):
        report_slow = create_autospec(CoverageReport)
        report_slow_header = create_autospec(CoverageReport)
        report_header = create_autospec(CoverageReport)
        report = create_autospec(CoverageReport)

        config_slow = PlainCommandlineConfiguration(["--slow"]).freeze()
        config_slow_header = PlainCommandlineConfiguration([
            "--slow", "--header"
        ]).freeze()
        config_header = PlainCommandlineConfiguration(["--header"]).freeze()
        config = PlainCommandlineConfiguration([]).freeze()

        config_report_map = ConfigCoverageReportMapping({
            config_slow: report_slow,
            config_slow_header: report_slow_header,
            config_header: report_header,
            config: report
        })

        self.assertEqual(
            config_report_map.available_features, set(["slow", "header"])
        )

        expected = [
            {
                "slow": True,
                "header": False
            },
            {
                "slow": True,
                "header": True
            },
        ]
        actual = config_report_map._get_configs_with_features({"slow": True})
        self.assertEqual(expected, actual)
        expected = [
            {
                "slow": False,
                "header": True
            },
            {
                "slow": False,
                "header": False
            },
        ]
        actual = config_report_map._get_configs_with_features({"slow": False})
        self.assertEqual(expected, actual)

        self.assertEqual(
            config_report_map._get_configs_with_features({"slow": False}),
            config_report_map._get_configs_without_features({"slow": True})
        )
        expected = [
            {
                "slow": True,
                "header": True
            },
        ]
        actual = config_report_map._get_configs_with_features({
            "slow": True,
            "header": True
        })
        self.assertEqual(expected, actual)

        expected = [
            {
                "slow": True,
                "header": False
            },
            {
                "slow": False,
                "header": True
            },
            {
                "slow": False,
                "header": False
            },
        ]
        actual = config_report_map._get_configs_without_features({
            "slow": True,
            "header": True
        })
        self.assertEqual(expected, actual)
        expected = [
            {
                "slow": True,
                "header": False
            },
            {
                "slow": True,
                "header": True
            },
            {
                "slow": False,
                "header": True
            },
            {
                "slow": False,
                "header": False
            },
        ]
        actual = config_report_map._get_configs_with_features({})
        self.assertEqual(expected, actual)

        expected = []
        actual = config_report_map._get_configs_without_features({})
        self.assertEqual(expected, actual)
        self.assertRaises(ValueError, lambda: config_report_map.diff({}))
        self.assertRaises(
            ValueError, lambda: config_report_map.diff({"foobar": True})
        )
