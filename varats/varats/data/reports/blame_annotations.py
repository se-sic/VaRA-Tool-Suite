"""Module for BlameAnnotations, mapping instructions to blame information."""
import typing as tp
from pathlib import Path

import yaml

from varats.base.version_header import VersionHeader
from varats.report.report import BaseReport


class BlameInstruction():
    """Collection of debug blame and VaRA blame."""

    def __init__(self, dbg_hash: str, vara_computed_hash: str) -> None:
        self.__dbg_hash = dbg_hash
        self.__vara_computed_hash = vara_computed_hash

    @staticmethod
    def create_blame_instruction(
        raw_entry: tp.Dict[str, tp.Any]
    ) -> 'BlameInstruction':
        """Creates a :class`BlameInstrucion`from the corresponding yaml document
        section."""
        dbg_hash = str(raw_entry['dbghash'])
        vara_computed_hash = str(raw_entry['varahash'])
        return BlameInstruction(dbg_hash, vara_computed_hash)

    @property
    def dbg_hash(self) -> str:
        """Blame based on debug information."""
        return self.__dbg_hash

    @property
    def vara_computed_hash(self) -> str:
        """
        Blame based on IRegion.

        Can be produced in different ways, based on which flag is used.
        """
        return self.__vara_computed_hash


class BlameFunctionAnnotations():
    """Contains all instruction annotations for one function."""

    def __init__(self) -> None:
        self.__blame_annotations: tp.Dict[str, BlameInstruction] = {}

    def add_annotation(self, name: str, inst: BlameInstruction) -> None:
        self.__blame_annotations[name] = inst

    @property
    def blame_annotations(self) -> tp.Dict[str, BlameInstruction]:
        """Iterate over all blame annotations."""
        return self.__blame_annotations


class BlameAnnotations(BaseReport, shorthand="BA", file_type="yaml"):
    """Report containing debug blame and blame annotations."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__functions = {}

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("BlameAnnotations")

            raw_blame_report = next(documents)

            for func in raw_blame_report['functions']:
                new_func = BlameFunctionAnnotations()
                func_entry = raw_blame_report['functions'][func]
                for raw_entry in func_entry['annotations']:
                    new_entry = (
                        BlameInstruction.create_blame_instruction(
                            func_entry['annotations'][raw_entry]
                        )
                    )
                    new_func.add_annotation(raw_entry, new_entry)
                self.__functions[func] = new_func

    @property
    def functions(self) -> tp.ValuesView[BlameFunctionAnnotations]:
        """Iterate over all blame annotations."""
        return self.__functions.values()


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

    for func in ast_ba.functions:
        for entry in func.blame_annotations.values():
            if entry.dbg_hash and entry.vara_computed_hash:
                ast_report.update_dbg_ast(
                    entry.dbg_hash != entry.vara_computed_hash
                )

    for line_func, ast_func in zip(line_ba.functions, ast_ba.functions):
        line_annotations = line_func.blame_annotations
        ast_annotations = ast_func.blame_annotations
        for inst in ast_annotations:
            if line_annotations[inst].vara_computed_hash and ast_annotations[
                inst].vara_computed_hash:
                ast_report.update_line_ast(
                    line_annotations[inst].vara_computed_hash !=
                    ast_annotations[inst].vara_computed_hash
                )

    return ast_report
