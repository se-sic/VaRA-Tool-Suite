"""Test VaRA commit reports."""

import typing as tp
import unittest
import unittest.mock as mock
from pathlib import Path

import yaml

from varats.data.reports.commit_report import (
    CommitReport,
    FunctionGraphEdges,
    FunctionInfo,
    RegionMapping,
    generate_interactions,
)
from varats.mapping.commit_map import CommitMap
from varats.report.report import FileStatusExtension, ReportFilename
from varats.utils.git_util import FullCommitHash, ShortCommitHash

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
    """Test if function infos are reconstruction from yaml."""

    finfos: tp.Dict[str, FunctionInfo]

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_2)
        ):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.finfos = {}
                for raw_finfo in yaml_doc['function-info']:
                    finfo = FunctionInfo(raw_finfo)
                    cls.finfos[finfo.name] = finfo

    def test_function_infos(self) -> None:
        """Test if function infos where parsed correctly."""
        bi_init = self.finfos["bi_init"]
        self.assertEqual(bi_init.id, "bi_init")
        self.assertEqual(bi_init.id, bi_init.name)
        self.assertEqual(
            bi_init.region_id, "b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"
        )

        send_bits = self.finfos["send_bits"]
        self.assertEqual(send_bits.id, "send_bits")
        self.assertEqual(send_bits.id, send_bits.name)
        self.assertEqual(
            send_bits.region_id, "8ac1b3f73baceb4a16e99504807d23d38e5123b1"
        )


class TestRegionMapping(unittest.TestCase):
    """Test if region mappings are reconstruction from yaml."""

    r_mappings: tp.Dict[str, RegionMapping]

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse region mappings from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_2)
        ):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.r_mappings = {}
                for raw_r_mapping in yaml_doc['region-mapping']:
                    r_mapping = RegionMapping(raw_r_mapping)
                    cls.r_mappings[r_mapping.id] = r_mapping

    def test_id_hash_mapping(self) -> None:
        """Test if id -> hash mappings are correct."""
        self.assertEqual(
            self.r_mappings["8ac1b3f73baceb4a16e99504807d23d38e5123b1"].hash,
            FullCommitHash("8ac1b3f73baceb4a16e99504807d23d38e5123b1")
        )

        self.assertEqual(
            self.r_mappings["38f87b03c2763bb2af05ae98905b0ac8ba55b3eb"].hash,
            FullCommitHash("38f87b03c2763bb2af05ae98905b0ac8ba55b3eb")
        )


class TestFunctionGraphEdges(unittest.TestCase):
    """Test function graph edges reconstruction from yaml."""

    edge_dict: tp.Dict[str, FunctionGraphEdges]

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse FunctionGraphEdges from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_3)
        ):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.edge_dict = {}
                for raw_fg_edges in yaml_doc:
                    f_edge = FunctionGraphEdges(raw_fg_edges)
                    cls.edge_dict[f_edge.fid] = f_edge

    def test_function_id(self) -> None:
        """Verify if IDs are correctly loaded."""
        bi_init = self.edge_dict['bi_init']
        self.assertEqual(bi_init.fid, "bi_init")

    def test_function_id_2(self) -> None:
        """Verify if IDs are correctly loaded."""
        send_bits = self.edge_dict['send_bits']
        self.assertEqual(send_bits.fid, "send_bits")

    def test_call_graph_edges(self) -> None:
        """Check if call-graph edges are parsed correctly."""
        bi_init = self.edge_dict['bi_init']
        self.assertEqual(
            bi_init.cg_edges[0].region,
            "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5"
        )
        self.assertEqual(bi_init.cg_edges[0].function, "llvm.dbg.value")

    def test_control_flow_edges(self) -> None:
        """Check if control-flow edges are parsed correctly."""
        bi_init = self.edge_dict['bi_init']
        self.assertEqual(
            bi_init.cf_edges[0].edge_from,
            "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5"
        )
        self.assertEqual(
            bi_init.cf_edges[0].edge_to,
            "b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"
        )

        self.assertEqual(
            bi_init.cf_edges[1].edge_from,
            "95ace546d3f6c5909a636017f141784105f9dab2"
        )
        self.assertEqual(
            bi_init.cf_edges[1].edge_to,
            "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5"
        )

    def test_data_flow_edges(self) -> None:
        """Check if data-flow edges are parsed correctly."""
        bi_init = self.edge_dict['bi_init']
        self.assertEqual(
            bi_init.df_relations[0].edge_from,
            "b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"
        )
        self.assertEqual(
            bi_init.df_relations[0].edge_to,
            "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5"
        )

        self.assertEqual(
            bi_init.df_relations[1].edge_from,
            "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5"
        )
        self.assertEqual(
            bi_init.df_relations[1].edge_to,
            "95ace546d3f6c5909a636017f141784105f9dab2"
        )


class TestCommitReport(unittest.TestCase):
    """Test basic CommitReport functionality."""

    commit_report: CommitReport
    commit_report_success: CommitReport
    commit_report_fail: CommitReport
    success_filename: str
    fail_filename: str

    @classmethod
    def setUpClass(cls) -> None:
        """Setup file and CommitReport."""
        file_content = YAML_DOC_1 + YAML_DOC_2 + YAML_DOC_3

        cls.success_filename = (
            "CR-foo-foo-7bb9ef5f8c_"
            "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be_"
            "success.yaml"
        )
        cls.fail_filename = (
            "CR-foo-foo-7bb9ef5f8c_"
            "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be"
            "_failed.txt"
        )

        with mock.patch(
            'builtins.open', new=mock.mock_open(read_data=file_content)
        ):
            cls.commit_report = CommitReport(Path("fake_file_path"))
            cls.commit_report_success = CommitReport(Path(cls.success_filename))
            cls.commit_report_fail = CommitReport(Path(cls.fail_filename))

    def test_path(self) -> None:
        """Check if path is set correctly."""
        self.assertEqual(self.commit_report.path, Path("fake_file_path"))

    def test_calc_max_func_edges(self) -> None:
        """Check if max edges are correctly calculated."""
        self.assertEqual(self.commit_report.calc_max_cf_edges(), 2)
        self.assertEqual(self.commit_report.calc_max_df_edges(), 3)

    def test_is_result_file(self) -> None:
        """Check if the result file matcher works."""
        self.assertTrue(self.commit_report_success.filename.is_result_file())
        self.assertTrue(self.commit_report_fail.filename.is_result_file())

        self.assertFalse(
            ReportFilename(
                self.commit_report_success.filename.filename.replace("_", "")
            ).is_result_file()
        )
        self.assertFalse(
            ReportFilename(
                self.commit_report_success.filename.filename.replace("-", "")
            ).is_result_file()
        )
        self.assertFalse(
            ReportFilename(
                self.commit_report_success.filename.filename.replace(".", "f")
            ).is_result_file()
        )

    def test_file_status(self) -> None:
        """Check if the correct file status is returned for CommitReport
        names."""
        self.assertTrue(
            self.commit_report_success.filename.has_status_success()
        )
        self.assertFalse(self.commit_report_fail.filename.has_status_success())

        self.assertTrue(self.commit_report_fail.filename.has_status_failed())
        self.assertFalse(
            self.commit_report_success.filename.has_status_failed()
        )

    def test_get_commit(self) -> None:
        """Check if the correct commit hash is returned."""
        self.assertEqual(
            self.commit_report_success.filename.commit_hash,
            ShortCommitHash("7bb9ef5f8c")
        )
        self.assertEqual(
            self.commit_report_fail.filename.commit_hash,
            ShortCommitHash("7bb9ef5f8c")
        )

    def test_file_name_creation(self) -> None:
        """Check if file names are created correctly."""
        self.assertEqual(
            CommitReport.get_file_name(
                "foo", "foo", "7bb9ef5f8c",
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be",
                FileStatusExtension.SUCCESS
            ), self.success_filename
        )

        self.assertEqual(
            CommitReport.get_file_name(
                "foo", "foo", "7bb9ef5f8c",
                "fdb09c5a-4cee-42d8-bbdc-4afe7a7864be",
                FileStatusExtension.FAILED, ".txt"
            ), self.fail_filename
        )


RAW_COMMIT_LOG = """20540be6186c159880dda3a49a5827722c1a0ac9
8aa53f1797315a541960d4225f00c9f27c9612fe
a604573c68ae41e1126229dfeab5b63bfb3848c8
e48a9161759686b9097edf392f8fa95c504b040b
8ebed06de292295267c4c3628417762945c24214
9c2a2de9a4c192c43b64ed42509d9e51f69aac44
d2e7cf947f228339b516b7491de46faed9b0d475
afd5c5938c6350d12fe4c4791ed5383a81469d64
17f5c70d3f049a6e8c5415a7d6961654aba1a497
361618d9cf28d91f07aa0a363df6b4d231d569dd
3909cddc8e9a434dd9c346f1da596879dee2d00f
62e1b9e30bc8a3bed955493c9a1b157561fff903
26c140cf5377585d38d2a13a949e109724d4d406
051ed82baa1090c4723b7addce64681bb417d3a9
8b83dc0f588ccaed3bd7e37208cefab2ff4edb28
30ba4a2b69e5ee34c3fcde12f275f80d1fbe8a59
1252d056feaf71e7488cbaa5a78b3d45cd77f877
bce795d0a38ae10f13b3297f1253acdeb4defc21
222dc8c90f31f7027d0aa7a18206f5c56006f780
9ef6a8ac4470aeac60445c7e4802349bc9272d5d
38f87b03c2763bb2af05ae98905b0ac8ba55b3eb
b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5
95ace546d3f6c5909a636017f141784105f9dab2
203e40cc4558a80998d05eb74b373a51e796ca8b
8ac1b3f73baceb4a16e99504807d23d38e5123b1
7868e29c3faca087be3790ab78ba570c3018bcb7
4c09ea0df417a948ded14ca890d34405c02347f6
0078b8a5a38f2cce0fd3f0994210f2cad5ec23b8
63aa2268a5abfed0116d04bbe3952e4a753af91d
975508caa09d733099498ff9f7b8079cd71d7109
ae332f2a5d2f6f3e0a23443f8a9bcb068c8af74d
ef58a957a6c1887930cc70d6199ae7e48aa8d716"""


def testing_gen_commit_map() -> CommitMap:
    """Generate a local commit map for testing."""

    def commit_log_stream() -> tp.Generator[str, None, None]:
        for number, line in enumerate(reversed(RAW_COMMIT_LOG.split('\n'))):
            yield "{}, {}\n".format(number, line)

    return CommitMap(commit_log_stream())


class TestCommitMap(unittest.TestCase):
    """Test CommitMap generation and Usage."""

    cmap: CommitMap

    @classmethod
    def setUpClass(cls) -> None:
        """Setup file and CommitReport."""

        cls.cmap = testing_gen_commit_map()

    def test_time_id(self) -> None:
        """Test time id look up."""
        self.assertEqual(
            self.cmap.time_id(
                FullCommitHash("ae332f2a5d2f6f3e0a23443f8a9bcb068c8af74d")
            ), 1
        )
        self.assertEqual(
            self.cmap.time_id(
                FullCommitHash("ef58a957a6c1887930cc70d6199ae7e48aa8d716")
            ), 0
        )
        self.assertEqual(
            self.cmap.time_id(
                FullCommitHash("20540be6186c159880dda3a49a5827722c1a0ac9")
            ), 32
        )

    def test_short_time_id(self) -> None:
        """Test short time id look up."""
        self.assertEqual(
            self.cmap.short_time_id(ShortCommitHash("ae332f2a5d")), 1
        )
        self.assertEqual(
            self.cmap.short_time_id(ShortCommitHash("ef58a957a6c1")), 0
        )
        self.assertEqual(
            self.cmap.short_time_id(ShortCommitHash("20540be618")), 32
        )


class TestCommitConnectionGenerators(unittest.TestCase):
    """Test basic CommitReport functionality."""

    commit_report: CommitReport
    cmap: CommitMap

    @classmethod
    def setUpClass(cls) -> None:
        """Setup file and CommitReport."""
        file_content = YAML_DOC_1 + YAML_DOC_2 + YAML_DOC_3
        with mock.patch(
            'builtins.open', new=mock.mock_open(read_data=file_content)
        ):
            cls.commit_report = CommitReport(Path("fake_file_path"))

        cls.cmap = testing_gen_commit_map()

    def test_gen_interactions_nodes(self) -> None:
        """Test generation of interaction node."""
        nodes = generate_interactions(self.commit_report, self.cmap)[0]
        self.assertEqual(
            nodes.at[0, 'hash'],
            FullCommitHash('38f87b03c2763bb2af05ae98905b0ac8ba55b3eb')
        )
        self.assertEqual(nodes.at[0, 'id'], 12)
        self.assertEqual(
            nodes.at[3, 'hash'],
            FullCommitHash('95ace546d3f6c5909a636017f141784105f9dab2')
        )
        self.assertEqual(nodes.at[3, 'id'], 9)

    def test_gen_interactions_links(self) -> None:
        """Test generation of interaction links."""
        links = generate_interactions(self.commit_report, self.cmap)[1]
        links = links.sort_values(by=['source']).reset_index(drop=True)
        self.assertEqual(
            links.at[0, 'source'], "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5"
        )
        self.assertEqual(
            links.at[0, 'target'], "b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"
        )
        self.assertEqual(links.at[0, 'value'], 1)
        self.assertEqual(links.at[0, 'src_id'], 10)

        self.assertEqual(
            links.at[2, 'source'], "95ace546d3f6c5909a636017f141784105f9dab2"
        )
        self.assertEqual(
            links.at[2, 'target'], "3ea7fe86ac3c1a887038e0e3e1c07ba4634ad1a5"
        )
        self.assertEqual(links.at[2, 'value'], 1)
        self.assertEqual(links.at[2, 'src_id'], 9)
