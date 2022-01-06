"""Test varats casestudy tool."""

import unittest
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import (
    run_in_test_environment,
    TEST_INPUTS_DIR,
    UnitTestInputs,
)
from varats.paper_mgmt.paper_config import load_paper_config
from varats.tools import driver_casestudy
from varats.utils.settings import vara_cfg, save_config


class TestDriverCaseStudy(unittest.TestCase):
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

    @run_in_test_environment(
        UnitTestInputs.create_test_input(
            TEST_INPUTS_DIR / "paper_configs/test_casestudy_status",
            Path("paper_configs/test_status")
        )
    )
    def test_vara_cs_status(self):
        """Test for vara-cs status."""
        runner = CliRunner()
        vara_cfg()["paper_config"]["current_config"] = "test_status"
        save_config()
        load_paper_config()
        result = runner.invoke(driver_casestudy.main, ['status', 'EmptyReport'])

        self.assertEqual(
            "CS: xz_0: (  0/5) processed [0/0/0/3/2]\n"
            "    c5c7ceb08a [Missing]\n"
            "    ef364d3abc [Missing]\n"
            "    2f0bc9cd40 [Missing]\n"
            "    7521bbdc83 [Blocked]\n"
            "    10437b5b56 [Blocked]\n\n"
            "---------------------------------------------"
            "-----------------------------------\n"
            "Total: (  0/5) processed [0/0/0/3/2]\n", result.stdout
        )
