"""Module for FeatureAnalysisReport."""

import re
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

    def is_terminator(self) -> bool:
        br_regex = re.compile(r'(br( i1 | label ))|(switch i\d{1,} )')
        return br_regex.search(self.__instruction) is not None


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
    ) -> 'FeatureAnalysisReportMetaData':
        """Creates `FeatureAnalysisReportMetaData` from the corresponding yaml
        document."""
        num_functions = int(raw_document['funcs-in-module'])
        num_instructions = int(raw_document['insts-in-module'])
        num_br_switch_insts = int(raw_document['br-switch-insts-in-module'])

        return FeatureAnalysisReportMetaData(
            num_functions, num_instructions, num_br_switch_insts
        )


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

    def get_feature_locations_dict(self) -> tp.Dict[str, tp.Set[str]]:
        """Returns a dictionary that maps a feature name to a list of all
        locations of tainted br and switch instructions."""
        feat_loc_dict: tp.Dict[str, tp.Set[str]] = {}
        for function_entry in self.__function_entries.values():
            for tainted_inst in function_entry.feature_tainted_insts:
                for feature in tainted_inst.feature_taints:
                    if tainted_inst.is_terminator():
                        if feature not in feat_loc_dict:
                            feat_loc_dict[feature] = set()
                        feat_loc_dict[feature].add(tainted_inst.location)
        return feat_loc_dict


class FeatureAnalysisGroundTruth():
    """Data Class that gives access to a loaded ground truth of a
    `FeatureAnalysisReport`."""

    def __init__(self, gt_path: Path) -> None:
        self.__path = gt_path
        with open(gt_path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            self.__locations: tp.Dict[str, tp.List[str]] = (next(documents))

    @property
    def path(self) -> Path:
        """Path to ground truth file."""
        return self.__path

    def get_feature_locations(self, feature: str) -> tp.Set[str]:
        """Get the locations of a specific feature."""
        return set(self.__locations[feature])

    def get_features(self) -> tp.List[str]:
        """Get a list of all features in the ground truth."""
        return list(self.__locations.keys())


class FeatureAnalysisReportEval():
    """
    Class that evaluates a `FeatureAnalysisReport` with a
    `FeatureAnalysisGroundTruth`.

    Is given a list of features for providing feature-specific evaluation
    information.
    """

    def __init__(
        self, fa_report: FeatureAnalysisReport,
        ground_truth: FeatureAnalysisGroundTruth, features: tp.List[str]
    ) -> None:
        self.__initialize_eval_data(features)
        self.__evaluate(fa_report, ground_truth)

    def __initialize_eval_data(self, features: tp.List[str]) -> None:
        self.__evaluation_data: tp.Dict[str, tp.Dict[str, int]] = {}
        features.append('Total')
        for feature in features:
            self.__evaluation_data[feature] = {
                'true_pos': 0,
                'false_pos': 0,
                'false_neg': 0,
                'true_neg': 0
            }

    def __evaluate(
        self, fa_report: FeatureAnalysisReport,
        ground_truth: FeatureAnalysisGroundTruth
    ) -> None:
        true_pos, false_pos, false_neg, true_neg = (0, 0, 0, 0)

        gt_features = ground_truth.get_features()
        for feature in gt_features:
            feat_true_pos, feat_false_pos, feat_false_neg, feat_true_neg = (
                0, 0, 0, 0
            )

            gt_locations = ground_truth.get_feature_locations(feature)
            fta_locations = fa_report.get_feature_locations_dict()[feature]

            feat_true_pos = len(gt_locations.intersection(fta_locations))
            feat_false_pos = len(fta_locations.difference(gt_locations))
            feat_false_neg = len(gt_locations.difference(fta_locations))
            feat_true_neg = (
                fa_report.meta_data.num_br_switch_insts - feat_true_pos -
                feat_false_pos - feat_false_neg
            )

            true_pos += feat_true_pos
            false_pos += feat_false_pos
            false_neg += feat_false_neg
            true_neg += feat_true_neg

            if feature in self.__evaluation_data:

                self.__evaluation_data[feature]['true_pos'] = feat_true_pos
                self.__evaluation_data[feature]['false_pos'] = feat_false_pos
                self.__evaluation_data[feature]['false_neg'] = feat_false_neg
                self.__evaluation_data[feature]['true_neg'] = feat_true_neg

        self.__evaluation_data['Total']['true_pos'] = true_pos
        self.__evaluation_data['Total']['false_pos'] = false_pos
        self.__evaluation_data['Total']['false_neg'] = false_neg
        self.__evaluation_data['Total']['true_neg'] = true_neg

    def get_true_pos(self, entry: str = 'Total') -> int:
        """
        Get the number of true positive taints either for a specific feature or
        the whole report.

        Args:
            feature : str, deafult 'Total'
                The name of the entry to look up.
        """
        return self.__evaluation_data[entry]['true_pos']

    def get_false_pos(self, entry: str = 'Total') -> int:
        """
        Get the number of false positive taints either for a specific feature or
        the whole report.

        Args:
            feature : str, deafult 'Total'
                The name of the entry to look up.
        """
        return self.__evaluation_data[entry]['false_pos']

    def get_false_neg(self, entry: str = 'Total') -> int:
        """
        Get the number of false negative taints either for a specific feature or
        the whole report.

        Args:
            feature : str, deafult 'Total'
                The name of the entry to look up.
        """
        return self.__evaluation_data[entry]['false_neg']

    def get_true_neg(self, entry: str = 'Total') -> int:
        """
        Get the number of true negative taints either for a specific feature or
        the whole report.

        Args:
            feature : str, deafult 'Total'
                The name of the entry to look up.
        """
        return self.__evaluation_data[entry]['true_neg']
