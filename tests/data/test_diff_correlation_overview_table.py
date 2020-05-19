import unittest

from tests.test_utils import replace_config


class TestDiffCorrelationOverviewTable(unittest.TestCase):

    @replace_config
    def test_replace_config(self, config):
        print("Test is running")
        config['data_cache'] = "Hello"
        print(f"config['data_cache'] = {config['data_cache']}")
