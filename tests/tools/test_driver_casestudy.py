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
            vara_cfg()["paper_config"]["folder"].value +
            "/test_gen/gravity_0.case_study"
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

    @run_in_test_environment(
        UnitTestInputs.create_test_input(
            TEST_INPUTS_DIR / "results/brotli", Path("results/brotli")
        ),
        UnitTestInputs.create_test_input(
            TEST_INPUTS_DIR / "paper_configs/test_revision_lookup",
            Path("paper_configs/test_cleanup_error")
        )
    )
    def test_vara_cs_cleanup_error(self):
        """Test vara-cs cleanup error."""
        runner = CliRunner()
        vara_cfg()["paper_config"]["current_config"] = "test_cleanup_error"
        save_config()
        load_paper_config()

        runner.invoke(driver_casestudy.main, ['cleanup', 'error'])
        self.assertFalse(
            Path(
                vara_cfg()["result_dir"].value +
                "/brotli/CRE-CR-brotli-all-6c47009892_5d26c7ff-6d27-478f-bcd1"
                "-99e8e8e97f16_cerror.txt"
            ).exists()
        )
        self.assertFalse(
            Path(
                vara_cfg()["result_dir"].value +
                "/brotli/CRE-CR-brotli-all-aaa4424d9b_5d26c7ff-6d27-478f-bcd1-"
                "99e8e8e97f16_failed.txt"
            ).exists()
        )
        self.assertTrue(
            Path(
                vara_cfg()["result_dir"].value +
                "/brotli/CRE-CR-brotli-brotli-21ac39f7c8_34d4d1b5-7212-4244-"
                "9adc-b19bff599cf1_success.yaml"
            ).exists()
        )

    @run_in_test_environment(
        UnitTestInputs.create_test_input(
            TEST_INPUTS_DIR / "results/brotli", Path("results/brotli")
        ),
        UnitTestInputs.create_test_input(
            TEST_INPUTS_DIR / "results/gravity", Path("results/gravity")
        ),
        UnitTestInputs.create_test_input(
            TEST_INPUTS_DIR / "paper_configs/test_revision_lookup",
            Path("paper_configs/test_cleanup_regex")
        )
    )
    def test_vara_cs_cleanup_regex(self):
        """Test vara-cs cleanup regex."""
        runner = CliRunner()
        vara_cfg()["paper_config"]["current_config"] = "test_cleanup_regex"
        save_config()
        load_paper_config()
        runner.invoke(
            driver_casestudy.main, ['cleanup', 'regex', '-f', '.*'], 'y'
        )
        self.assertFalse(
            Path(
                vara_cfg()["result_dir"].value +
                "/brotli/CRE-CR-brotli-all-6c47009892_5d26c7ff-6d27-478f-bcd1-"
                "99e8e8e97f16_cerror.txt"
            ).exists()
        )
        self.assertFalse(
            Path(
                vara_cfg()["result_dir"].value +
                "/brotli/CRE-CR-brotli-all-aaa4424d9b_5d26c7ff-6d27-478f-bcd1-"
                "99e8e8e97f16_failed.txt"
            ).exists()
        )
        self.assertFalse(
            Path(
                vara_cfg()["result_dir"].value +
                "/brotli/CRE-CR-brotli-brotli-21ac39f7c8_34d4d1b5-7212-4244-"
                "9adc-b19bff599cf1_success.yaml"
            ).exists()
        )
        self.assertFalse(
            Path(
                vara_cfg()["result_dir"].value +
                "/brotli/CRE-CR-brotli-brotli-21ac39f7c8_34d4d1b5-7212-4244-"
                "9adc-b19bff599142_success.yaml"
            ).exists()
        )
        self.assertTrue(
            Path(
                vara_cfg()["result_dir"].value +
                "/gravity/BVRE_NoOptTBAA-BVR_NoOpt_TBAA-gravity-gravity-"
                "b51227de55_8bc2ac4c-b6e3-43d1-aff9-c6b32126b155_success.txt"
            ).exists()
        )
