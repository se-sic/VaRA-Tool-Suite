"""Module for FeatureAnalysisReport."""

import typing as tp
from pathlib import Path

import yaml

from varats.base.version_header import VersionHeader
from varats.report.report import BaseReport


class FeatureTaintedInstruction():
    """An instruction that is tainted with one or more features and its location
    in the project."""

    def __init__(
        self, instruction: str, location: str, feature_taints: tp.List[str]
    ) -> None:
        self.__instruction = instruction
        self.__location = location
        self.__feature_taints = sorted(feature_taints)

    @staticmethod
    def create_feature_tainted_instruction(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> 'FeatureTaintedInstruction':
        """Creates a `FeatureTaintedInstruction` entry from the corresponding
        yaml document section."""
        instruction = str(raw_inst_entry['inst'])
        location = str(raw_inst_entry['location'])
        feat_taints: tp.List[str] = []
        for taint in raw_inst_entry['taints']:
            feat_taints.append(str(taint))
        return FeatureTaintedInstruction(instruction, location, feat_taints)

    @property
    def instruction(self) -> str:
        """Feature tainted instruction."""
        return self.__instruction

    @property
    def location(self) -> str:
        """Location of instruction in the project."""
        return self.__location

    @property
    def feature_taints(self) -> tp.List[str]:
        """List of features related to the instruction."""
        return self.__feature_taints

    def __eq__(self, other: tp.Any) -> bool:
        if isinstance(other, FeatureTaintedInstruction):
            return (
                self.instruction == other.instruction and
                self.location == other.location and
                self.feature_taints == other.feature_taints
            )

        return False


class FeatureAnalysisResultFunctionEntry():
    """Collection of all feature tainted instructions for a specific
    function."""

    def __init__(
        self, name: str, demangled_name: str,
        feature_tainted_insts: tp.List[FeatureTaintedInstruction]
    ) -> None:
        self.__name = name
        self.__demangled_name = demangled_name
        self.__feature_tainted_insts = feature_tainted_insts

    @staticmethod
    def create_feature_analysis_result_function_entry(
        name: str, raw_function_entry: tp.Dict[str, tp.Any]
    ) -> 'FeatureAnalysisResultFunctionEntry':
        """Creates a `FeatureAnalysisResultFunctionEntry` from the corresponding
        yaml document section."""
        demangled_name = str(raw_function_entry['demangled-name'])
        inst_list: tp.List[FeatureTaintedInstruction] = []
        for raw_inst_entry in raw_function_entry['feature-related-insts']:
            inst_list.append(
                FeatureTaintedInstruction.
                create_feature_tainted_instruction(raw_inst_entry)
            )
        return FeatureAnalysisResultFunctionEntry(
            name, demangled_name, inst_list
        )

    @property
    def name(self) -> str:
        """
        Name of the function.

        The name is mangled for C++ code, either with the itanium or windows
        mangling schema.
        """
        return self.__name

    @property
    def demangled_name(self) -> str:
        """Demangled name of the function."""
        return self.__demangled_name

    @property
    def feature_tainted_insts(self) -> tp.List[FeatureTaintedInstruction]:
        """List of found feature tainted instructions."""
        return self.__feature_tainted_insts


class FeatureAnalysisReportMetaData():
    """Provides extra meta data about llvm::Module, which was analyzed to
    generate this ``FeatureAnalysisReport``."""

    def __init__(
        self,
        num_functions: int,
        num_instructions: int,
    ) -> None:
        self.__number_of_functions_in_module = num_functions
        self.__number_of_instructions_in_module = num_instructions

    @property
    def num_functions(self) -> int:
        """Number of functions in the analyzed llvm::Module."""
        return self.__number_of_functions_in_module

    @property
    def num_instructions(self) -> int:
        """Number of instructions processed in the analyzed llvm::Module."""
        return self.__number_of_instructions_in_module

    @staticmethod
    def create_feature_analysis_report_meta_data(
        raw_document: tp.Dict[str, tp.Any]
    ) -> 'FeatureAnalysisReportMetaData':
        """Creates `FeatureAnalysisReportMetaData` from the corresponding yaml
        document."""
        num_functions = int(raw_document['funcs-in-module'])
        num_instructions = int(raw_document['insts-in-module'])

        return FeatureAnalysisReportMetaData(num_functions, num_instructions)


class FeatureAnalysisReport(BaseReport, shorthand="FAR", file_type="yaml"):
    """Data class that gives access to a loaded feature analysis report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("FeatureAnalysisReport")
            version_header.raise_if_version_is_less_than(1)

            self.__meta_data = FeatureAnalysisReportMetaData \
                .create_feature_analysis_report_meta_data(next(documents))

            self.__function_entries: tp.Dict[
                str, FeatureAnalysisResultFunctionEntry] = {}
            raw_feature_analysis_report = next(documents)
            for raw_func_entry in raw_feature_analysis_report['result-map']:
                new_function_entry = (
                    FeatureAnalysisResultFunctionEntry.
                    create_feature_analysis_result_function_entry(
                        raw_func_entry,
                        raw_feature_analysis_report['result-map']
                        [raw_func_entry]
                    )
                )
                self.__function_entries[new_function_entry.name
                                       ] = new_function_entry

    @property
    def meta_data(self) -> FeatureAnalysisReportMetaData:
        """Access the meta data that was gathered with the
        ``FeatureAnalysisReport``."""
        return self.__meta_data

    @property
    def function_entries(
        self
    ) -> tp.ValuesView[FeatureAnalysisResultFunctionEntry]:
        """Iterate over all function entries."""
        return self.__function_entries.values()

    def get_feature_analysis_result_function_entry(
        self, mangled_function_name: str
    ) -> FeatureAnalysisResultFunctionEntry:
        """
        Get the result entry for a specific function.

        Args:
            mangled_function_name: mangled name of the function to look up
        """
        return self.__function_entries[mangled_function_name]
