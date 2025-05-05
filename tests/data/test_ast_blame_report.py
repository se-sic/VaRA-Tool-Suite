"""Test VaRA AST blame reports."""
import unittest
from pathlib import Path
from unittest import mock

from varats.data.reports.blame_annotations import (
    BlameAnnotations,
    BlameComparisonReport,
    compare_blame_annotations,
)

FAKE_REPORT_PATH = (
    "BCE-BCR-lz4-lz4-bdc9d3b0c1_a68da96a-e52e-4254-b45f-753d0205d3e7_"\
      "success.yaml"
)

YAML_DOC_HEADER = """---
DocType:        BlameAnnotations
Version:        1
...
"""

YAML_DOC_BA_LINE = """---
functions:
  _Z19calculate_somethingi:
    annotations:
      - inst:            '  %x.addr = alloca i32, align 4'
        dbghash:         ''
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %result = alloca i32, align 4'
        dbghash:         ''
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  store i32 %x, i32* %x.addr, align 4'
        dbghash:         ''
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  call void @llvm.dbg.declare(metadata i32* %x.addr, metadata !16, metadata !DIExpression())'
        dbghash:         ''
        varahash:        ''
      - inst:            '  %0 = bitcast i32* %result to i8*'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  call void @llvm.lifetime.start.p0i8(i64 4, i8* %0) #5'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  call void @llvm.dbg.declare(metadata i32* %result, metadata !17, metadata !DIExpression())'
        dbghash:         ''
        varahash:        ''
      - inst:            '  %1 = load i32, i32* %x.addr, align 4'
        dbghash:         73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
        varahash:        73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
      - inst:            '  %add = add nsw i32 %1, 42'
        dbghash:         73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
        varahash:        73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
      - inst:            '  %sub = sub nsw i32 %add, 1'
        dbghash:         73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
        varahash:        73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
      - inst:            '  store i32 %sub, i32* %result, align 4'
        dbghash:         73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
        varahash:        73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
      - inst:            '  %2 = load i32, i32* %result, align 4'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %3 = bitcast i32* %result to i8*'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  call void @llvm.lifetime.end.p0i8(i64 4, i8* %3) #5'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  ret i32 %2'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
  main:
    annotations:
      - inst:            '  %call = call noundef i32 @_Z19calculate_somethingi(i32 noundef 4)'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %call1 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([3 x i8], [3 x i8]* @.str, i64 0, i64 0), i32 noundef %call)'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  ret i32 0'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
...
"""

YAML_DOC_BA_AST = """---
functions:
  _Z19calculate_somethingi:
    annotations:
      - inst:            '  %x.addr = alloca i32, align 4'
        dbghash:         ''
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %result = alloca i32, align 4'
        dbghash:         ''
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  store i32 %x, i32* %x.addr, align 4'
        dbghash:         ''
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  call void @llvm.dbg.declare(metadata i32* %x.addr, metadata !16, metadata !DIExpression())'
        dbghash:         ''
        varahash:        ''
      - inst:            '  %0 = bitcast i32* %result to i8*'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  call void @llvm.lifetime.start.p0i8(i64 4, i8* %0) #5'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  call void @llvm.dbg.declare(metadata i32* %result, metadata !17, metadata !DIExpression())'
        dbghash:         ''
        varahash:        ''
      - inst:            '  %1 = load i32, i32* %x.addr, align 4'
        dbghash:         73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %add = add nsw i32 %1, 42'
        dbghash:         73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %sub = sub nsw i32 %add, 1'
        dbghash:         73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
        varahash:        73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
      - inst:            '  store i32 %sub, i32* %result, align 4'
        dbghash:         73b69c2c4b1ab80e5e9dcf24c3280ca9f394f20f
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %2 = load i32, i32* %result, align 4'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %3 = bitcast i32* %result to i8*'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  call void @llvm.lifetime.end.p0i8(i64 4, i8* %3) #5'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  ret i32 %2'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
  main:
    annotations:
      - inst:            '  %call = call noundef i32 @_Z19calculate_somethingi(i32 noundef 4)'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  %call1 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([3 x i8], [3 x i8]* @.str, i64 0, i64 0), i32 noundef %call)'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
      - inst:            '  ret i32 0'
        dbghash:         16c99ec75c6f40538f812b22f11ce69b54e58147
        varahash:        16c99ec75c6f40538f812b22f11ce69b54e58147
...
"""

YAML_DOC_BCR = """
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


class TestBlameComparisonReport(unittest.TestCase):
    """Test if AST blame report is correctly reconstructed from yaml."""

    report: BlameComparisonReport

    @classmethod
    def setUpClass(cls) -> None:
        """Create BlameComparisonReport."""
        cls.report = BlameComparisonReport(Path('fake_file_path'))

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
