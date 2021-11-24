"""Test varats casestudy tool."""
import re
import unittest
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment
from varats.paper_mgmt.paper_config import load_paper_config
from varats.tools import driver_casestudy
from varats.utils.settings import vara_cfg, save_config


class TestDriverContainer(unittest.TestCase):
    """Tests for the driver_casestudy module."""

    @run_in_test_environment()
    def test_vara_cs_gen(self):
        """Test for vara-cs gen."""
        runner = CliRunner()
        Path(vara_cfg()["paper_config"]["folder"].value + "/" +
             "test_gen").mkdir()
        runner.invoke(
            driver_casestudy.main, [
                'gen', '-p', 'gravity', '--distribution',
                'HalfNormalSamplingMethod', 'paper_configs/test_gen'
            ]
        )
        case_study = Path(
            vara_cfg()["paper_config"]["folder"].value + "/" + "test_gen"
            "/" + "gravity_0.case_study"
        )
        self.assertTrue(case_study.exists())

    @run_in_test_environment()
    def test_vara_cs_status(self):
        """Test for vara-cs status."""
        runner = CliRunner()
        (Path(vara_cfg()["paper_config"]["folder"].value) /
         "test_status").mkdir()
        vara_cfg()["paper_config"]["current_config"] = "test_status"
        save_config()

        runner.invoke(
            driver_casestudy.main, [
                'gen', '-p', 'gravity', '--distribution',
                'HalfNormalSamplingMethod', 'paper_configs/test_status'
            ]
        )
        load_paper_config()
        case_study = Path(
            vara_cfg()["paper_config"]["folder"].value + "/" + "test_status"
            "/" + "gravity_0.case_study"
        )
        self.assertTrue(case_study.exists())

        result = runner.invoke(driver_casestudy.main, ['status', 'EmptyReport'])

        self.assertTrue(case_study.exists())
        self.assertTrue(
            re.match(
                r'CS:\sgravity_0:\s\(\s\s\d\/\d\d\)\sprocessed\s\[\d\/\d\/\d\/\d\/\d\].*',
                result.stdout
            )
        )
