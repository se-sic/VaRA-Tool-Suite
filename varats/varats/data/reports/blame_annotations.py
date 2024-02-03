"""Module for BlameAnnotations, mapping instructions to blame information."""
import typing as tp
from pathlib import Path

import yaml

from varats.base.version_header import VersionHeader
from varats.report.report import BaseReport


class BlameInstruction():
    """Collection of debug blame and VaRA blame."""

    def __init__(self, dbghash: str, varahash: str) -> None:
        self.__dbghash = dbghash
        self.__varahash = varahash

    @staticmethod
    def create_blame_instruction(
        raw_entry: tp.Dict[str, tp.Any]
    ) -> 'BlameInstruction':
        """Creates a :class`BlameInstrucion`from the corresponding yaml document
        section."""
        dbghash = str(raw_entry['dbghash'])
        varahash = str(raw_entry['varahash'])
        return BlameInstruction(dbghash, varahash)

    @property
    def dbghash(self) -> str:
        """Blame based on debug information."""
        return self.__dbghash

    @property
    def varahash(self) -> str:
        """Blame based on IRegion."""
        return self.__varahash


class BlameAnnotations(BaseReport, shorthand="BA", file_type="yaml"):
    """Report containing debug blame and blame annotations."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__blame_annotations = {}

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("BlameAnnotations")

            raw_blame_report = next(documents)

            for raw_entry in raw_blame_report['annotations']:
                new_entry = (
                    BlameInstruction.create_blame_instruction(
                        raw_blame_report['annotations'][raw_entry]
                    )
                )
                self.__blame_annotations[raw_entry] = new_entry

    @property
    def blame_annotations(self) -> tp.ValuesView[BlameInstruction]:
        """Iterate over all blame annotations."""
        return self.__blame_annotations.values()


class ASTBlameReport(BaseReport, shorthand="BAST", file_type="yaml"):
    """Report containing difference between AST-based and line-based blame."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__diff_dbg_ast = 0
        self.__eq_dbg_ast = 0
        self.__diff_line_ast = 0
        self.__eq_line_ast = 0

    def print_yaml(self) -> None:
        """Writes the result of the comparison to a yaml file."""
        data = {
            'dbg vs ast': {
                'diff': self.__diff_dbg_ast,
                'equal': self.__eq_dbg_ast
            },
            'line vs ast': {
                'diff': self.__diff_line_ast,
                'equal': self.__eq_line_ast
            }
        }
        with open(self.path, 'w') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False)

    def update_dbg_ast(self, diff: bool) -> None:
        """Updates the metrics of the comparison between debug and AST based
        information."""
        if diff:
            self.__diff_dbg_ast += 1
        else:
            self.__eq_dbg_ast += 1

    def update_line_ast(self, diff: bool) -> None:
        """Updates the metrics of the comparison between line based and AST
        based information."""
        if diff:
            self.__diff_line_ast += 1
        else:
            self.__eq_line_ast += 1

    @property
    def diff_dbg_ast(self) -> int:
        """Count of different instructions between debug and ast blame."""
        return self.__diff_dbg_ast

    @property
    def eq_dbg_ast(self) -> int:
        """Count of equal instructions between debug and ast blame."""
        return self.__eq_dbg_ast

    @property
    def diff_line_ast(self) -> int:
        """Count of different instructions between line and ast blame."""
        return self.__diff_line_ast

    @property
    def eq_line_ast(self) -> int:
        """Count of equal instructions between line and ast blame."""
        return self.__eq_line_ast


def compare_blame_annotations(
    line_ba: BlameAnnotations, ast_ba: BlameAnnotations, path: Path
) -> ASTBlameReport:
    """Compares the debug based to the AST based annotations as well as the line
    based to the AST based blame."""
    ast_report = ASTBlameReport(path)

    for entry in ast_ba.blame_annotations:
        ast_report.update_dbg_ast(entry.dbghash != entry.varahash)

    for line_entry, ast_entry in zip(
        line_ba.blame_annotations, ast_ba.blame_annotations
    ):
        ast_report.update_line_ast(line_entry.varahash != ast_entry.varahash)

    return ast_report
