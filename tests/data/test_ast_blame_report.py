"""Test VaRA AST blame reports."""
import unittest
from pathlib import Path
from unittest import mock

from varats.data.reports.blame_annotations import (
    BlameAnnotations,
    ASTBlameReport,
    compare_blame_annotations,
)

FAKE_REPORT_PATH = (
    "BASTE-BAST-lz4-lz4-bdc9d3b0c1_a68da96a-e52e-4254-b45f-753d0205d3e7_"\
      "success.yaml"
)

YAML_DOC_HEADER = """---
DocType:        BlameAnnotations
Version:        1
...
"""

YAML_DOC_BA_LINE = """---
annotations:
  0=bitcasti32*resulttoi8*,!dbg!23,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  1=loadi32,i32*x.addr,align4,!dbg!25,!tbaa!18,!BlameRegion!26:
    dbghash:         2b9a08d1adb63d2db9283811f79ac66e373ccfe9
    varahash:        2b9a08d1adb63d2db9283811f79ac66e373ccfe9
  2=loadi32,i32*result,align4,!dbg!31,!tbaa!18,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  3=bitcasti32*resulttoi8*,!dbg!32,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  add=addnswi321,42,!dbg!28,!BlameRegion!26:
    dbghash:         2b9a08d1adb63d2db9283811f79ac66e373ccfe9
    varahash:        2b9a08d1adb63d2db9283811f79ac66e373ccfe9
  call1=calli32(i8*,...)@printf(i8*noundefgetelementptrinbounds([3xi8],[3xi8]*@.str,i640,i640),i32noundefcall),!dbg!17,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  call=callnoundefi32@_Z19calculate_somethingi(i32noundef4),!dbg!16,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  callvoid@llvm.dbg.declare(metadatai32*result,metadata!17,metadata!DIExpression()),!dbg!24:
    dbghash:         ''
    varahash:        ''
  callvoid@llvm.dbg.declare(metadatai32*x.addr,metadata!16,metadata!DIExpression()),!dbg!22:
    dbghash:         ''
    varahash:        ''
  callvoid@llvm.lifetime.end.p0i8(i644,i8*3)#5,!dbg!32,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  callvoid@llvm.lifetime.start.p0i8(i644,i8*0)#5,!dbg!23,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  result=allocai32,align4,!BlameRegion!0:
    dbghash:         ''
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  reti320,!dbg!18,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  reti322,!dbg!33,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  storei32sub,i32*result,align4,!dbg!30,!tbaa!18,!BlameRegion!26:
    dbghash:         2b9a08d1adb63d2db9283811f79ac66e373ccfe9
    varahash:        2b9a08d1adb63d2db9283811f79ac66e373ccfe9
  storei32x,i32*x.addr,align4,!tbaa!18,!BlameRegion!0:
    dbghash:         ''
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  sub=subnswi32add,1,!dbg!29,!BlameRegion!26:
    dbghash:         2b9a08d1adb63d2db9283811f79ac66e373ccfe9
    varahash:        2b9a08d1adb63d2db9283811f79ac66e373ccfe9
  x.addr=allocai32,align4,!BlameRegion!0:
    dbghash:         ''
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
...
"""

YAML_DOC_BA_AST = """---
annotations:
  0=bitcasti32*resulttoi8*,!dbg!23,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  1=loadi32,i32*x.addr,align4,!dbg!25,!tbaa!18,!BlameRegion!0:
    dbghash:         2b9a08d1adb63d2db9283811f79ac66e373ccfe9
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  2=loadi32,i32*result,align4,!dbg!31,!tbaa!18,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  3=bitcasti32*resulttoi8*,!dbg!32,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  add=addnswi321,42,!dbg!26,!BlameRegion!0:
    dbghash:         2b9a08d1adb63d2db9283811f79ac66e373ccfe9
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  call1=calli32(i8*,...)@printf(i8*noundefgetelementptrinbounds([3xi8],[3xi8]*@.str,i640,i640),i32noundefcall),!dbg!17,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  call=callnoundefi32@_Z19calculate_somethingi(i32noundef4),!dbg!16,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  callvoid@llvm.dbg.declare(metadatai32*result,metadata!17,metadata!DIExpression()),!dbg!24:
    dbghash:         ''
    varahash:        ''
  callvoid@llvm.dbg.declare(metadatai32*x.addr,metadata!16,metadata!DIExpression()),!dbg!22:
    dbghash:         ''
    varahash:        ''
  callvoid@llvm.lifetime.end.p0i8(i644,i8*3)#5,!dbg!32,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  callvoid@llvm.lifetime.start.p0i8(i644,i8*0)#5,!dbg!23,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  result=allocai32,align4,!BlameRegion!0:
    dbghash:         ''
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  reti320,!dbg!18,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  reti322,!dbg!33,!BlameRegion!0:
    dbghash:         2553b819d9434f3396727617438dc0d6ae39b056
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  storei32sub,i32*result,align4,!dbg!30,!tbaa!18,!BlameRegion!0:
    dbghash:         2b9a08d1adb63d2db9283811f79ac66e373ccfe9
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  storei32x,i32*x.addr,align4,!tbaa!18,!BlameRegion!0:
    dbghash:         ''
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
  sub=subnswi32add,1,!dbg!27,!BlameRegion!28:
    dbghash:         2b9a08d1adb63d2db9283811f79ac66e373ccfe9
    varahash:        2b9a08d1adb63d2db9283811f79ac66e373ccfe9
  x.addr=allocai32,align4,!BlameRegion!0:
    dbghash:         ''
    varahash:        2553b819d9434f3396727617438dc0d6ae39b056
...
"""

YAML_DOC_BAST = """
dbg vs ast:
  diff: 3
  equal: 10
line vs ast:
  diff: 3
  equal: 13
"""


class TestBlameAnnotaions(unittest.TestCase):
    """Test if blame annotation entrries are correctly reconstructed from
    yaml."""

    blame_annotations: BlameAnnotations

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse annotation infos from yaml file."""
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=YAML_DOC_HEADER + YAML_DOC_BA_LINE)
        ):
            loaded_report = BlameAnnotations(Path('fake_file_path'))
            cls.blame_annotations = loaded_report

    def test_path(self) -> None:
        """Test if the path is saved correctly."""
        self.assertEqual(self.blame_annotations.path, Path("fake_file_path"))


class TestASTBlameReport(unittest.TestCase):
    """Test if AST blame report is correctly reconstructed from yaml."""

    report: ASTBlameReport

    @classmethod
    def setUpClass(cls) -> None:
        """Create ASTBlameReport."""
        cls.report = ASTBlameReport(Path('fake_file_path'))

    def test_path(self) -> None:
        """Test if the path is saved correctly."""
        self.assertEqual(self.report.path, Path("fake_file_path"))

    def test_update_dbg_ast(self) -> None:
        """Test function update_dbg_ast."""
        self.assertEqual(self.report.diff_dbg_ast, 0)
        self.assertEqual(self.report.eq_dbg_ast, 0)
        self.report.update_dbg_ast(True)
        self.assertEqual(self.report.diff_dbg_ast, 1)
        self.assertEqual(self.report.eq_dbg_ast, 0)
        self.report.update_dbg_ast(False)
        self.assertEqual(self.report.diff_dbg_ast, 1)
        self.assertEqual(self.report.eq_dbg_ast, 1)

    def test_update_line_ast(self) -> None:
        """Test function update_dbg_ast."""
        self.assertEqual(self.report.diff_line_ast, 0)
        self.assertEqual(self.report.eq_line_ast, 0)
        self.report.update_line_ast(True)
        self.assertEqual(self.report.diff_line_ast, 1)
        self.assertEqual(self.report.eq_line_ast, 0)
        self.report.update_line_ast(False)
        self.assertEqual(self.report.diff_line_ast, 1)
        self.assertEqual(self.report.eq_line_ast, 1)


class TestBlameASTComparison(unittest.TestCase):
    """Test if the blame comparison works correctly."""

    line_report: BlameAnnotations
    ast_report: BlameAnnotations

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse annotations infos from yaml files."""
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=YAML_DOC_HEADER + YAML_DOC_BA_LINE)
        ):
            cls.line_report = BlameAnnotations(Path('fake_report_path'))
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=YAML_DOC_HEADER + YAML_DOC_BA_AST)
        ):
            cls.ast_report = BlameAnnotations(Path('fake_report_path'))

    def test_compare_blame_annotations(self) -> None:
        """Test function compare_blame_annotations."""
        comparison_report = compare_blame_annotations(
            self.line_report, self.ast_report, Path('fake_report_path')
        )
        self.assertEqual(comparison_report.diff_dbg_ast, 3)
        self.assertEqual(comparison_report.eq_dbg_ast, 10)
        self.assertEqual(comparison_report.diff_line_ast, 3)
        self.assertEqual(comparison_report.eq_line_ast, 13)
