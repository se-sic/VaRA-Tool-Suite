"""Test varats casestudy tool."""
import unittest
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.tools import driver_casestudy
from varats.utils.settings import vara_cfg


class TestDriverContainer(unittest.TestCase):
    """Tests for the driver_casestudy module."""

    @run_in_test_environment()
    def test_vara_cs_gen(self):
        """Test for vara-cs gen."""
        runner = CliRunner()
        Path(vara_cfg()["paper_config"]["folder"].value + "/" + "test").mkdir()
        runner.invoke(
            driver_casestudy.main, [
                'gen', '-p', 'xz', '--distribution', 'UniformSamplingMethod',
                'paper_configs/test'
            ]
        )
        case_study = Path(
            vara_cfg()["paper_config"]["folder"].value + "/" + "test"
            "/" + "xz_0.case_study"
        )
        self.assertTrue(case_study.exists())
