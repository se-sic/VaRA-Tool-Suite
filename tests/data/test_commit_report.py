"""
Test VaRA commit reports.
"""

import unittest
import unittest.mock as mock

import yaml

from varats.data.commit_report import FunctionGraphEdges, FunctionInfo,\
    RegionMapping, CommitReport

YAML_DOC_1 = """---
DocType:         CommitReport
Version:         3
...
"""

YAML_DOC_2 = """---
function-info:
  - id:              bi_init
    region-id:       b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
    function-name:   bi_init
  - id:              send_bits
    region-id:       8ac1b3f73baceb4a16e99504807d23d38e5123b1
    function-name:   send_bits
region-mapping:
  - id:              8ac1b3f73baceb4a16e99504807d23d38e5123b1
    hash:            8ac1b3f73baceb4a16e99504807d23d38e5123b1
  - id:              38f87b03c2763bb2af05ae98905b0ac8ba55b3eb
    hash:            38f87b03c2763bb2af05ae98905b0ac8ba55b3eb
  - id:              b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
    hash:            b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
  - id:              3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
    hash:            3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
  - id:              95ace546d3f6c5909a636017f141784105f9dab2
    hash:            95ace546d3f6c5909a636017f141784105f9dab2
...
"""

YAML_DOC_3 = """---
- function-id:     bi_init
  call-graph-edges:
    - from-region:     3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
      to-functions:
        - llvm.dbg.value
    - from-region:     b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
      to-functions:
        - flush_outbuf
  control-flow-edges:
    - from:            3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
      to:              b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
    - from:            95ace546d3f6c5909a636017f141784105f9dab2
      to:              3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
  data-flow-relations:
    - from:            b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
      to:              3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
    - from:            3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
      to:              95ace546d3f6c5909a636017f141784105f9dab2
- function-id:     send_bits
  call-graph-edges:
    - from-region:     3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
      to-functions:
        - llvm.dbg.value
  control-flow-edges:
    - from:            3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
      to:              b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
  data-flow-relations:
    - from:            b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
      to:              95ace546d3f6c5909a636017f141784105f9dab2
    - from:            3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
      to:              95ace546d3f6c5909a636017f141784105f9dab2
...
"""


class TestFunctionInfo(unittest.TestCase):
    """
    Test if function infos are reconstruction from yaml.
    """

    @classmethod
    def setUpClass(cls):
        """
        Load and parse function infos from yaml file.
        """
        with mock.patch("builtins.open",
                        new=mock.mock_open(read_data=YAML_DOC_2)):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.finfos = {}
                for raw_finfo in yaml_doc['function-info']:
                    finfo = FunctionInfo(raw_finfo)
                    cls.finfos[finfo.name] = finfo

    def test_function_infos(self):
        """
        Test if function infos where parsed correctly.
        """
        bi_init = self.finfos["bi_init"]
        self.assertEqual(bi_init.id, "bi_init")
        self.assertEqual(bi_init.id, bi_init.name)
        self.assertEqual(bi_init.region_id,
                         "b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a")

        send_bits = self.finfos["send_bits"]
        self.assertEqual(send_bits.id, "send_bits")
        self.assertEqual(send_bits.id, send_bits.name)
        self.assertEqual(send_bits.region_id,
                         "8ac1b3f73baceb4a16e99504807d23d38e5123b1")


class TestRegionMapping(unittest.TestCase):
    """
    Test if region mappings are reconstruction from yaml.
    """

    @classmethod
    def setUpClass(cls):
        """
        Load and parse region mappings from yaml file.
        """
        with mock.patch("builtins.open",
                        new=mock.mock_open(read_data=YAML_DOC_2)):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.r_mappings = {}
                for raw_r_mapping in yaml_doc['region-mapping']:
                    r_mapping = RegionMapping(raw_r_mapping)
                    cls.r_mappings[r_mapping.id] = r_mapping

    def test_id_hash_mapping(self):
        """
        Test if id -> hash mappings are correct.
        """
        self.assertEqual(
            self.r_mappings["8ac1b3f73baceb4a16e99504807d23d38e5123b1"].hash,
            "8ac1b3f73baceb4a16e99504807d23d38e5123b1")

        self.assertEqual(
            self.r_mappings["38f87b03c2763bb2af05ae98905b0ac8ba55b3eb"].hash,
            "38f87b03c2763bb2af05ae98905b0ac8ba55b3eb")


class TestFunctionGraphEdges(unittest.TestCase):
    """
    Test function graph edges reconstruction from yaml.
    """

    @classmethod
    def setUpClass(cls):
        """
        Load and parse FunctionGraphEdges from yaml file.
        """
        with mock.patch("builtins.open",
                        new=mock.mock_open(read_data=YAML_DOC_3)):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.edge_dict = {}
                for raw_fg_edges in yaml_doc:
                    f_edge = FunctionGraphEdges(raw_fg_edges)
                    cls.edge_dict[f_edge.fid] = f_edge

    def test_function_id(self):
        """
        Verify if IDs are correctly loaded.
        """
        bi_init = self.edge_dict['bi_init']
        self.assertEqual(bi_init.fid, "bi_init")

    def test_function_id_2(self):
        """
        Verify if IDs are correctly loaded.
        """
        send_bits = self.edge_dict['send_bits']
        self.assertEqual(send_bits.fid, "send_bits")

    def test_call_graph_edges(self):
        """
        Check if call-graph edges are parsed correctly.
        """
        bi_init = self.edge_dict['bi_init']
        self.assertEqual(bi_init.cg_edges[0].region,
                         "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5")
        self.assertEqual(bi_init.cg_edges[0].function,
                         "llvm.dbg.value")

    def test_control_flow_edges(self):
        """
        Check if control-flow edges are parsed correctly.
        """
        bi_init = self.edge_dict['bi_init']
        self.assertEqual(bi_init.cf_edges[0].edge_from,
                         "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5")
        self.assertEqual(bi_init.cf_edges[0].edge_to,
                         "b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a")

        self.assertEqual(bi_init.cf_edges[1].edge_from,
                         "95ace546d3f6c5909a636017f141784105f9dab2")
        self.assertEqual(bi_init.cf_edges[1].edge_to,
                         "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5")

    def test_data_flow_edges(self):
        """
        Check if data-flow edges are parsed correctly.
        """
        bi_init = self.edge_dict['bi_init']
        self.assertEqual(bi_init.df_relations[0].edge_from,
                         "b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a")
        self.assertEqual(bi_init.df_relations[0].edge_to,
                         "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5")

        self.assertEqual(bi_init.df_relations[1].edge_from,
                         "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5")
        self.assertEqual(bi_init.df_relations[1].edge_to,
                         "95ace546d3f6c5909a636017f141784105f9dab2")


class TestCommitReport(unittest.TestCase):
    """
    Test basic CommitReport functionality.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup file and CommitReport
        """
        file_content = YAML_DOC_1 + YAML_DOC_2 + YAML_DOC_3
        with mock.patch('builtins.open',
                        new=mock.mock_open(read_data=file_content)):
            cls.commit_report = CommitReport("fake_file_path")

    def test_path(self):
        """
        Check if path is set correctly.
        """
        self.assertEqual(self.commit_report.path, "fake_file_path")

    def test_calc_max_func_edges(self):
        """
        Check if max edges are correctly calculated.
        """
        self.assertEqual(self.commit_report.calc_max_cf_edges(), 2)
        self.assertEqual(self.commit_report.calc_max_df_edges(), 3)
