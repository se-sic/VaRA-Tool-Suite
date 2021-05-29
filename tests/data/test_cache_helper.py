"""Test the cache_helper module."""
import unittest

import pandas as pd

from tests.test_utils import run_in_test_environment
from varats.data.cache_helper import (
    build_cached_report_table,
    get_data_file_path,
)


class TestCacheHelper(unittest.TestCase):
    """Test the cache_helper module."""

    TEST_DATA = {
        "a": ("a", 1),
        "a2": ("a", 2),
        "b": ("b", 1),
        "c": ("c", 1),
        "c2": ("c", 2),
    }

    @run_in_test_environment()
    def test_get_data_file_path(self):
        path = get_data_file_path("foo", "tmux")
        self.assertEqual("data_cache/foo-tmux.csv.gz", str(path))

    @run_in_test_environment()
    def test_build_cached_report_table(self):
        """Check whether data items are correctly cached and updated/evicted."""
        data_id = "cache_test_data"
        project_name = "project"

        def create_empty_df():
            return pd.DataFrame(columns=["entry"])

        def create_cache_entry_data(entry: str):
            return pd.DataFrame({"entry": entry}, index=[
                0
            ]), get_entry_id(entry), get_entry_timestamp(entry)

        def get_entry_id(entry: str) -> str:
            return self.TEST_DATA[entry][0]

        def get_entry_timestamp(entry: str) -> str:
            return str(self.TEST_DATA[entry][1])

        def is_newer_timestamp(ts1: str, ts2: str) -> bool:
            return int(ts1) > int(ts2)

        # initialize cache with a,b,c
        df = build_cached_report_table(
            data_id, project_name, ["a", "b", "c"], [], create_empty_df,
            create_cache_entry_data, get_entry_id, get_entry_timestamp,
            is_newer_timestamp
        )

        self.assertIn("a", df["entry"].values)
        self.assertIn("b", df["entry"].values)
        self.assertIn("c", df["entry"].values)

        # update c -> c2 and "update" b -> b
        df = build_cached_report_table(
            data_id, project_name, ["b", "c2"], [], create_empty_df,
            create_cache_entry_data, get_entry_id, get_entry_timestamp,
            is_newer_timestamp
        )

        self.assertIn("a", df["entry"].values)
        self.assertIn("b", df["entry"].values)
        self.assertNotIn("c", df["entry"].values)
        self.assertIn("c2", df["entry"].values)

        # delete a via a2
        df = build_cached_report_table(
            data_id, project_name, [], ["a"], create_empty_df,
            create_cache_entry_data, get_entry_id, get_entry_timestamp,
            is_newer_timestamp
        )

        self.assertNotIn("a2", df["entry"].values)
        self.assertIn("b", df["entry"].values)
        self.assertIn("c2", df["entry"].values)
