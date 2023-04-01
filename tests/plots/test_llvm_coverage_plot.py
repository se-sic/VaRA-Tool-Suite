import unittest
from unittest.mock import create_autospec

from varats.base.configuration import PlainCommandlineConfiguration
from varats.data.reports.llvm_coverage_report import CodeRegion, CoverageReport
from varats.varats.plots.llvm_coverage_plot import (
    RunConfig,
    ConfigCoverageReportMapping,
)

CODE_REGION_1 = CodeRegion.from_list([9, 79, 17, 2, 4, 0, 0, 0], "main")


class TestCodeRegion(unittest.TestCase):

    def test_feature_config_report_map(self):
        report_slow = create_autospec(CoverageReport)
        report_slow_header = create_autospec(CoverageReport)
        report_header = create_autospec(CoverageReport)
        report = create_autospec(CoverageReport)

        config_slow = PlainCommandlineConfiguration(["--slow"])
        config_slow_header = PlainCommandlineConfiguration([
            "--slow", "--header"
        ])
        config_header = PlainCommandlineConfiguration(["--header"])
        config = PlainCommandlineConfiguration([])

        config_report_map = ConfigCoverageReportMapping({
            config_slow: report_slow,
            config_slow_header: report_slow_header,
            config_header: report_header,
            config: report
        })

        self.assertEqual(
            config_report_map.available_features, set(["--slow", "--header"])
        )

        expected = {
            RunConfig({
                "--slow": True,
                "--header": True
            }),
            RunConfig({
                "--slow": True,
                "--header": False
            }),
        }
        actual = config_report_map._get_configs_with_features({"--slow": True})
        self.assertEqual(expected, actual)
        expected = {
            RunConfig({
                "--slow": False,
                "--header": True
            }),
            RunConfig({
                "--slow": False,
                "--header": False
            }),
        }
        actual = config_report_map._get_configs_with_features({"--slow": False})
        self.assertEqual(expected, actual)

        self.assertEqual(
            config_report_map._get_configs_with_features({"--slow": False}),
            config_report_map._get_configs_without_features({"--slow": True})
        )
        expected = {
            RunConfig({
                "--slow": True,
                "--header": True
            }),
        }
        actual = config_report_map._get_configs_with_features({
            "--slow": True,
            "--header": True
        })
        self.assertEqual(expected, actual)

        expected = {
            RunConfig({
                "--slow": True,
                "--header": False
            }),
            RunConfig({
                "--slow": False,
                "--header": True
            }),
            RunConfig({
                "--slow": False,
                "--header": False
            }),
        }
        actual = config_report_map._get_configs_without_features({
            "--slow": True,
            "--header": True
        })
        self.assertEqual(expected, actual)
        expected = {
            RunConfig({
                "--slow": True,
                "--header": True
            }),
            RunConfig({
                "--slow": True,
                "--header": False
            }),
            RunConfig({
                "--slow": False,
                "--header": True
            }),
            RunConfig({
                "--slow": False,
                "--header": False
            }),
        }
        actual = config_report_map._get_configs_with_features({})
        self.assertEqual(expected, actual)

        expected = set()
        actual = config_report_map._get_configs_without_features({})
        self.assertEqual(expected, actual)
        self.assertRaises(ValueError, lambda: config_report_map.diff({}))
        self.assertRaises(
            ValueError, lambda: config_report_map.diff({"--foobar": True})
        )
