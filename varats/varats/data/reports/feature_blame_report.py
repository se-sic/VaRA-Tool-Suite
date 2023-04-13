"""Module for FeatureBlameReport."""

import re
import typing as tp
from pathlib import Path

import yaml

from varats.base.version_header import VersionHeader
from varats.report.report import BaseReport


class FeatureCommitRegion():
    """Data containing feature and commit regions."""
    def __init__(
        self, feature: str, commit_hash: str, repo: str
    ) -> None:
        self.__feature = feature
        self.__commit_hash = commit_hash
        self.__repo = repo

    @staticmethod
    def create_feature_commit_region(
        raw_region_data: tp.Dict[str, tp.Any]
    ) -> 'FeatureCommitRegion':
        feature = raw_region_data["feature"]
        commit_hash = raw_region_data["commit-hash"]
        repo = raw_region_data["repo"]
        return FeatureCommitRegion(feature, commit_hash, repo)
    
    def print(self) -> None:
        print("      -FEATURE COMMIT REGION")
        print("        -FEATURE: " + self.__feature)
        print("        -COMMIT HASH: " + self.__commit_hash)
        print("        -REPO: " + self.__repo)

    @property
    def feature(self) -> str:
        return self.__feature
    
    @property
    def commit_hash(self) -> str:
        return self.__commit_hash
    
    @property
    def repo(self) -> str:
        return self.__repo

class FeatureCommitRegionInstruction():
    """An instruction that has one or more feature-commit interaction and its location
    in the project."""

    def __init__(
        self, instruction: str, location: str, feature_commit_regions: tp.List[FeatureCommitRegion]
    ) -> None:
        self.__instruction = instruction
        self.__location = location
        self.__feature_commit_regions = feature_commit_regions
         

    @staticmethod
    def create_feature_tainted_instruction(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> 'FeatureCommitRegionInstruction':
        """Creates a `FeatureCommitRegionInstruction` entry from the corresponding
        yaml document section."""
        instruction = str(raw_inst_entry['inst'])
        location = str(raw_inst_entry['location'])
        feature_commit_regions: tp.List[FeatureCommitRegion] = []
        for fcr in raw_inst_entry['regions']:
            feature_commit_regions.append(FeatureCommitRegion.create_feature_commit_region(fcr))
        return FeatureCommitRegionInstruction(instruction, location, feature_commit_regions)


    def print(self) -> None:
        print("    -FEATURE COMMIT REGION INSTRUCTION")
        print("      -INSTRUCTION: " + self.__instruction)
        print("      -LOCATION: " + self.__location)
        for FCR in self.__feature_commit_regions:
            FCR.print()

    @property
    def instruction(self) -> str:
        """instruction containg commit and feature regions."""
        return self.__instruction

    @property
    def location(self) -> str:
        """Location of instruction in the project."""
        return self.__location

    @property
    def feature_commit_regions(self) -> tp.List[str]:
        """List of commit and feature regions of this instruction."""
        return self.__feature_commit_regions

    def is_terminator(self) -> bool:
        br_regex = re.compile(r'(br( i1 | label ))|(switch i\d{1,} )')
        return br_regex.search(self.__instruction) is not None


class FeatureBlameResultFunctionEntry():
    """Collection of all feature commit region instructions for a specific
    function."""

    def __init__(
        self, name: str, demangled_name: str,
        feature_commit_region_insts: tp.List[FeatureCommitRegionInstruction]
    ) -> None:
        self.__name = name
        self.__demangled_name = demangled_name
        self.__feature_commit_region_insts = feature_commit_region_insts


    @staticmethod
    def create_feature_blame_result_function_entry(
        name: str, raw_function_entry: tp.Dict[str, tp.Any]
    ) -> 'FeatureBlameResultFunctionEntry':
        """Creates a `FeatureBlameResultFunctionEntry` from the corresponding
        yaml document section."""
        demangled_name = str(raw_function_entry['demangled-name'])
        inst_list: tp.List[FeatureCommitRegionInstruction] = []
        for raw_inst_entry in raw_function_entry['commit-feature-interaction-related-insts']:
            inst_list.append(
                FeatureCommitRegionInstruction.
                create_feature_tainted_instruction(raw_inst_entry)
            )
        return FeatureBlameResultFunctionEntry(
            name, demangled_name, inst_list
        )
    
    def print(self) -> None:
        print("  -FEATURE BLAME RESULT FUNCTION ENTRY")
        print("    -FUNCTION: " + self.demangled_name)
        for FCRI in self.__feature_commit_region_insts:
            FCRI.print()

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
    def feature_commit_region_insts(self) -> tp.List[FeatureCommitRegionInstruction]:
        """List of found feature commit region instructions."""
        return self.__feature_commit_region_insts


class FeatureBlameReportMetaData():
    """Provides extra meta data about llvm::Module, which was analyzed to
    generate this ``FeatureBlameReport``."""

    def __init__(
        self, num_functions: int, num_instructions: int,
        num_br_switch_insts: int
    ) -> None:
        self.__number_of_functions_in_module = num_functions
        self.__number_of_instructions_in_module = num_instructions
        self.__number_of_branch_and_switch_ints_in_module = num_br_switch_insts

    @property
    def num_functions(self) -> int:
        """Number of functions in the analyzed llvm::Module."""
        return self.__number_of_functions_in_module

    @property
    def num_instructions(self) -> int:
        """Number of instructions processed in the analyzed llvm::Module."""
        return self.__number_of_instructions_in_module

    @property
    def num_br_switch_insts(self) -> int:
        """Number of branch and switch instructions processed in the analyzed
        llvm::Module."""
        return self.__number_of_branch_and_switch_ints_in_module

    @staticmethod
    def create_feature_analysis_report_meta_data(
        raw_document: tp.Dict[str, tp.Any]
    ) -> 'FeatureBlameReportMetaData':
        """Creates `FeatureBlameReportMetaData` from the corresponding yaml
        document."""
        num_functions = int(raw_document['funcs-in-module'])
        num_instructions = int(raw_document['insts-in-module'])
        num_br_switch_insts = int(raw_document['br-switch-insts-in-module'])

        return FeatureBlameReportMetaData(
            num_functions, num_instructions, num_br_switch_insts
        )

class FeatureBlameReport(BaseReport, shorthand="FBR", file_type="yaml"):
    """Data class that gives access to a loaded feature blame report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("FeatureBlameReport")
            version_header.raise_if_version_is_less_than(1)

            self.__meta_data = FeatureBlameReportMetaData \
                .create_feature_analysis_report_meta_data(next(documents))
            
            self.__function_entries: tp.Dict[
                str, FeatureBlameResultFunctionEntry] = {}
            raw_feature_blame_report = next(documents)
            for raw_func_entry in raw_feature_blame_report['result-map']:
                new_function_entry = (
                    FeatureBlameResultFunctionEntry.
                    create_feature_blame_result_function_entry(
                        raw_func_entry,
                        raw_feature_blame_report['result-map']
                        [raw_func_entry]
                    )
                )
                self.__function_entries[new_function_entry.name
                                       ] = new_function_entry
                

    def print(self) -> None:
        print("FEATURE BLAME REPORT")
        for FE in self.__function_entries.values():
            FE.print()

    @property
    def meta_data(self) -> FeatureBlameReportMetaData:
        """Access the meta data that was gathered with the
        ``FeatureBlameReport``."""
        return self.__meta_data
    
    @property
    def function_entries(
        self
    ) -> tp.ValuesView[FeatureBlameResultFunctionEntry]:
        """Iterate over all function entries."""
        return self.__function_entries.values()
    
    def get_feature_analysis_result_function_entry(
        self, mangled_function_name: str
    ) -> FeatureBlameResultFunctionEntry:
        """
        Get the result entry for a specific function.

        Args:
            mangled_function_name: mangled name of the function to look up
        """
        return self.__function_entries[mangled_function_name]

    def get_feature_locations_dict(self) -> tp.Dict[str, tp.Set[str]]:
        """Returns a dictionary that maps a feature name to a list of all
        locations of tainted br and switch instructions."""

