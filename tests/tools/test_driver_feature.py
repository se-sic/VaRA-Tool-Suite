import unittest
from functools import reduce

from click.testing import CliRunner

from tests.helper_utils import run_in_test_environment
from varats.tools import driver_feature


class TestDriverFeature(unittest.TestCase):
    """Tests for the driver_feature module."""

    @run_in_test_environment()
    def test_annotate(self):
        """Placeholder test."""
        runnner = CliRunner()
        result = runnner.invoke(
            driver_feature.main,
            ["annotate", "-p", "bzip2", "-r", "7b443720990", "-o", "test.xml"],
            input="y\nopMode\ny\nbzip2.c 175:9 175:14\nn\nn\n\n"
        )
        self.maxDiff = None
        self.assertEqual(
            result.stdout, "Annotate another feature? [y/N]: y\n"
            "Enter feature name to annotate: opMode\n"
            "Track another location for feature 'opMode'? [y/N]: y\n"
            "Enter location for feature opMode @ 7b44372099: bzip2.c 175:9 175:14\n"
            "Tracking 'opMode' at location bzip2.c 175:9 175:14\n"
            "Track another location for feature 'opMode'? [y/N]: n\n\n"
            "Annotate another feature? [y/N]: n\n\n"
            "[opMode @ 4c0d43f0f8] Annotation changed for 'opMode'.\n"
            "Old location: bzip2.c 175:9 175:14\n"
            "New location:  [bzip2.c 182:9 182:14:opMode]: \n\n\n\n\n\n"
            "Final annotations written to test.xml.\n"
        )
        with open("test.xml", "r") as f:
            content = reduce(lambda x, y: x + y.strip(), f.readlines())
            self.assertEqual(
                content, "Annotations for feature opMode:\n"
                "<sourceRange>"
                "<revisionRange>"
                "<introduced>"
                "7b443720990befbdc4c71865b6355841163f064e"
                "</introduced>"
                "<removed>"
                "4c0d43f0f861893dbc065adf03286880ecc754e5"
                "</removed></revisionRange>"
                "<path>bzip2.c</path>"
                "<start><line>175</line><column>9</column></start>"
                "<end><line>175</line><column>14</column></end>"
                "</sourceRange>"
                "<sourceRange><revisionRange><introduced>"
                "4c0d43f0f861893dbc065adf03286880ecc754e5"
                "</introduced></revisionRange>"
                "<path>bzip2.c</path>"
                "<start><line>182</line><column>9</column></start>"
                "<end><line>182</line><column>14</column></end>"
                "</sourceRange>"
            )
        self.assertEqual(0, result.exit_code, result.exception)
