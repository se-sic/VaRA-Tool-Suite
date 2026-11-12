import unittest
from functools import reduce
from pathlib import Path

from click.testing import CliRunner

from tests.helper_utils import run_in_test_environment
from varats.tools import driver_feature


class TestDriverFeature(unittest.TestCase):
    """Tests for the driver_feature module."""

    @run_in_test_environment()
    def test_annotate(self) -> None:
        """Placeholder test."""
        runnner = CliRunner()
        result = runnner.invoke(
            driver_feature.main,
            ["annotate", "-p", "bzip2", "-r", "7b443720990", "-o", "test.xml"],
            input="y\nopMode\ny\nbzip2.c 175:9 175:14\nn\nn\n\n",
        )
        self.maxDiff = None
        self.assertEqual(
            result.stdout,
            "Annotate another feature? [y/N]: y\n"
            "Enter feature name to annotate: opMode\n"
            "Track another location for feature 'opMode'? [y/N]: y\n"
            "Enter location for feature opMode @ 7b44372099: "
            "bzip2.c 175:9 175:14\n"
            "Tracking 'opMode' at location bzip2.c 175:9 175:14\n"
            "Track another location for feature 'opMode'? [y/N]: n\n\n"
            "Annotate another feature? [y/N]: n\n\n"
            "[opMode @ 4c0d43f0f8] Annotation changed for 'opMode'.\n"
            "Old location: bzip2.c 175:9 175:14\n"
            "New location:  [bzip2.c 182:9 182:14:opMode]: \n\n"
            "Final annotations written to test.xml.\n",
        )
        with Path("test.xml").open(encoding="utf-8") as f:
            content = reduce(lambda x, y: x + y.strip(), f.readlines())
            self.assertEqual(
                content,
                "Annotations for feature opMode:\n"
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
                "</sourceRange>",
            )
        self.assertEqual(0, result.exit_code, result.exception)

    @run_in_test_environment()
    def test_annotate_merges_into_feature_model(self) -> None:
        """New annotations are appended to the features of the infile."""
        Path("fm.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<vm><binaryOptions><configurationOption><name>opMode</name>"
            "<locations><sourceRange><revisionRange><introduced>"
            "0000000000000000000000000000000000000001"
            "</introduced></revisionRange><path>old.c</path>"
            "<start><line>1</line><column>1</column></start>"
            "</sourceRange></locations>"
            "</configurationOption></binaryOptions></vm>\n",
            encoding="utf-8",
        )
        result = CliRunner().invoke(
            driver_feature.main,
            [
                "annotate",
                "-p",
                "bzip2",
                "-r",
                "7b443720990",
                "-i",
                "fm.xml",
                "-o",
                "out.xml",
            ],
            input="y\nunknown\nopMode\ny\nbzip2.c 175:9 175:14\nn\nn\n\n",
        )
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("'unknown' is not 'opMode'", result.output)

        annotations = driver_feature.load_feature_model(Path("out.xml"))
        self.assertEqual(
            [str(a.location) for a in annotations["opMode"]],
            [
                "old.c 1:1 1:None",
                "bzip2.c 175:9 175:14",
                "bzip2.c 182:9 182:14",
            ],
        )
