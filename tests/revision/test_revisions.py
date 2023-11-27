"""Test revision helper functions."""

import unittest

from tests.helper_utils import run_in_test_environment, UnitTestFixtures
from varats.paper.paper_config import load_paper_config
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.settings import vara_cfg


class TestGetProcessedRevisionsFiles(unittest.TestCase):
    """Test if the revision look up works correctly."""

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_config_specific_lookup(self) -> None:
        """Check whether the config specific file loading works."""
        vara_cfg()['paper_config']['current_config'] = "test_config_ids"
        load_paper_config()

        processed_rev_files_cid_1 = get_processed_revisions_files(
            "SynthSAContextSensitivity", config_id=1
        )
        self.assertEqual(len(processed_rev_files_cid_1), 1)
        self.assertEqual(
            processed_rev_files_cid_1[0].report_filename.config_id, 1
        )
