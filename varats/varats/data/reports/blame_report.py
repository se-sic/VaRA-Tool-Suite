"""Module for BlameReport, a collection of blame interactions."""
import logging
import typing as tp
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from enum import Enum
from pathlib import Path

import numpy as np
import pygit2
import yaml

from varats.base.version_header import VersionHeader
from varats.report.report import BaseReport
from varats.utils.git_util import (
    map_commits,
    CommitRepoPair,
    CommitLookupTy,
    FullCommitHash,
    ShortCommitHash,
    UNCOMMITTED_COMMIT_HASH,
)

LOG = logging.getLogger(__name__)


class BlameTaintData():
    """Data that is carried by a blame taint."""

    def __init__(
        self,
        commit: CommitRepoPair,
        region_id: tp.Optional[int] = None,
        function_name: tp.Optional[str] = None
    ) -> None:
        # if region_id is present, so has to be function_name
        assert (region_id is None) or function_name

        self.__region_id: tp.Optional[int] = region_id
        self.__function_name: tp.Optional[str] = function_name
        self.__commit: CommitRepoPair = commit

    @staticmethod
    def create_taint_data(
        raw_taint_data: tp.Dict[str, tp.Any]
    ) -> 'BlameTaintData':
        """Create a :class:`BlameTaintData` instance from from the corresponding
        yaml document section."""
        commit = CommitRepoPair(
            FullCommitHash(raw_taint_data["commit"]),
            raw_taint_data["repository"]
        )
        return BlameTaintData(
            commit, raw_taint_data.get("region"),
            raw_taint_data.get("function")
        )

    @property
    def region_id(self) -> tp.Optional[int]:
        return self.__region_id

    @property
    def function_name(self) -> tp.Optional[str]:
        return self.__function_name

    @property
    def commit(self) -> CommitRepoPair:
        return self.__commit

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BlameTaintData):
            return NotImplemented

        return not ((self.region_id != other.region_id) or
                    (self.function_name != other.function_name) or
                    (self.commit != other.commit))

    def __lt_commit(self, other: 'BlameTaintData') -> bool:
        if other.function_name:
            return True
        return self.commit < other.commit

    def __lt_commit_in_function(self, other: 'BlameTaintData') -> bool:
        if not self.function_name:
            raise AssertionError()

        if not other.function_name:
            return False
        if other.region_id:
            return True
        return (
            self.function_name < other.function_name
            if self.function_name != other.function_name else
            self.commit < other.commit
        )

    def __lt_region(self, other: 'BlameTaintData') -> bool:
        if not self.region_id:
            raise AssertionError()
        if not other.region_id:
            return False
        return self.region_id < other.region_id

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, BlameTaintData):
            return NotImplemented

        # BTS_COMMIT
        if not self.function_name:
            return self.__lt_commit(other)

        # BTS_COMMIT_IN_FUNCTION
        if self.region_id is None:
            return self.__lt_commit_in_function(other)

        # BTS_REGION
        return self.__lt_region(other)

    def __hash__(self) -> int:
        return hash((self.commit, self.region_id, self.function_name))


class BlameInstInteractions():
    """
    An interaction between a base region/taint, attached to an instruction, and
    other regions/taints.

    For the blame analysis, these taints stem from data flows into the
    instruction.
    """

    def __init__(
        self, base_taint: BlameTaintData,
        interacting_taints: tp.List[BlameTaintData], amount: int
    ) -> None:
        self.__base_taint = base_taint
        self.__interacting_taints = sorted(interacting_taints)
        self.__amount = amount

    @staticmethod
    def create_blame_inst_interactions(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> 'BlameInstInteractions':
        """Creates a :class:`BlameInstInteractions` entry from the corresponding
        yaml document section."""

        def create_taint_data(
            raw_data: tp.Union[str, tp.Dict[str, tp.Any]]
        ) -> BlameTaintData:
            # be backwards compatible with blame report version 4
            if isinstance(raw_data, str):
                commit_hash, *repo = raw_data.split('-', maxsplit=1)
                crp = CommitRepoPair(
                    FullCommitHash(commit_hash), repo[0] if repo else "Unknown"
                )
                return BlameTaintData(crp)
            return BlameTaintData.create_taint_data(raw_data)

        base_taint = create_taint_data(raw_inst_entry['base-hash'])
        interacting_taints: tp.List[BlameTaintData] = []
        for raw_inst_taint in raw_inst_entry['interacting-hashes']:
            interacting_taints.append(create_taint_data(raw_inst_taint))
        amount = int(raw_inst_entry['amount'])
        return BlameInstInteractions(base_taint, interacting_taints, amount)

    @property
    def base_taint(self) -> BlameTaintData:
        """Base taint of the analyzed instruction."""
        return self.__base_taint

    @property
    def interacting_taints(self) -> tp.List[BlameTaintData]:
        """List of taints that interact with the base."""
        return self.__interacting_taints

    @property
    def amount(self) -> int:
        """Number of same interactions found in this function."""
        return self.__amount

    def __str__(self) -> str:
        str_representation = f"{self.base_taint} <-(# {self.amount:4})- ["
        sep = ""
        for interacting_taint in self.interacting_taints:
            str_representation += sep + str(interacting_taint)
            sep = ", "
        str_representation += "]\n"
        return str_representation

    def __eq__(self, other: tp.Any) -> bool:
        if isinstance(other, BlameInstInteractions):
            if self.base_taint == other.base_taint:
                return self.interacting_taints == other.interacting_taints

        return False

    def __lt__(self, other: tp.Any) -> bool:
        if isinstance(other, BlameInstInteractions):
            if self.base_taint != other.base_taint:
                return self.base_taint < other.base_taint
            return self.interacting_taints < other.interacting_taints

        return False


class BlameResultFunctionEntry():
    """Collection of all interactions for a specific function."""

    def __init__(
        self, name: str, demangled_name: str,
        blame_insts: tp.List[BlameInstInteractions], num_instructions: int
    ) -> None:
        self.__name = name
        self.__demangled_name = demangled_name
        self.__inst_list = blame_insts
        self.__num_instructions = num_instructions

    @staticmethod
    def create_blame_result_function_entry(
        name: str, raw_function_entry: tp.Dict[str, tp.Any]
    ) -> 'BlameResultFunctionEntry':
        """Creates a :class:`BlameResultFunctionEntry` from the corresponding
        yaml document section."""
        demangled_name = str(raw_function_entry['demangled-name'])
        num_instructions = int(raw_function_entry['num-instructions'])
        inst_list: tp.List[BlameInstInteractions] = []
        for raw_inst_entry in raw_function_entry['insts']:
            inst_list.append(
                BlameInstInteractions.
                create_blame_inst_interactions(raw_inst_entry)
            )
        return BlameResultFunctionEntry(
            name, demangled_name, inst_list, num_instructions
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
    def num_instructions(self) -> int:
        """Number of instructions in this function."""
        return self.__num_instructions

    @property
    def interactions(self) -> tp.List[BlameInstInteractions]:
        """List of found instruction blame-interactions."""
        return self.__inst_list

    def __str__(self) -> str:
        str_representation = f"{self.name} ({self.demangled_name})\n"
        for inst in self.__inst_list:
            str_representation += f"  - {inst}"
        return str_representation


def _calc_diff_between_func_entries(
    base_func_entry: BlameResultFunctionEntry,
    prev_func_entry: BlameResultFunctionEntry
) -> BlameResultFunctionEntry:
    diff_interactions: tp.List[BlameInstInteractions] = []

    # copy lists to avoid side effects
    base_interactions = list(base_func_entry.interactions)
    prev_interactions = list(prev_func_entry.interactions)

    # num instructions diff
    diff_num_instructions = abs(
        base_func_entry.num_instructions - prev_func_entry.num_instructions
    )

    for base_inter in base_interactions:
        if base_inter in prev_interactions:
            prev_inter_idx = prev_interactions.index(base_inter)
            prev_inter = prev_interactions.pop(prev_inter_idx)
            # create new blame inst interaction with the absolute difference
            # between base and prev
            difference = base_inter.amount - prev_inter.amount
            if difference != 0:
                diff_interactions.append(
                    BlameInstInteractions(
                        base_inter.base_taint,
                        deepcopy(base_inter.interacting_taints), difference
                    )
                )
        else:
            # append new interaction from base report
            diff_interactions.append(deepcopy(base_inter))

    # append left over interactions from previous blame report
    diff_interactions += prev_interactions

    return BlameResultFunctionEntry(
        base_func_entry.name, base_func_entry.demangled_name, diff_interactions,
        diff_num_instructions
    )


class BlameReportMetaData():
    """Provides extra meta-data about ``llvm::Module``, which was analyzed to
    generate this :class:`BlameReport`."""

    def __init__(
        self, num_functions: int, num_instructions: int,
        num_phasar_empty_tracked_vars: tp.Optional[int],
        num_phasar_total_tracked_vars: tp.Optional[int]
    ) -> None:
        self.__number_of_functions_in_module = num_functions
        self.__number_of_instructions_in_module = num_instructions
        self.__num_phasar_empty_tracked_vars = num_phasar_empty_tracked_vars
        self.__num_phasar_total_tracked_vars = num_phasar_total_tracked_vars

    @property
    def num_functions(self) -> int:
        """Number of functions in the analyzed llvm::Module."""
        return self.__number_of_functions_in_module

    @property
    def num_instructions(self) -> int:
        """Number of instructions processed in the analyzed llvm::Module."""
        return self.__number_of_instructions_in_module

    @property
    def num_empty_tracked_vars(self) -> tp.Optional[int]:
        """Number of variables tracked by phasar that had an empty taint set."""
        return self.__num_phasar_empty_tracked_vars

    @property
    def num_total_tracked_vars(self) -> tp.Optional[int]:
        """Number of variables tracked by phasar."""
        return self.__num_phasar_total_tracked_vars

    @staticmethod
    def create_blame_report_meta_data(
        raw_document: tp.Dict[str, tp.Any]
    ) -> 'BlameReportMetaData':
        """Creates :class:`BlameReportMetaData` from the corresponding yaml
        document."""
        num_functions = int(raw_document['funcs-in-module'])
        num_instructions = int(raw_document['insts-in-module'])
        num_phasar_empty_tracked_vars = int(
            raw_document["phasar-empty-tracked-vars"]
        ) if "phasar-empty-tracked-vars" in raw_document else None

        num_phasar_total_tracked_vars = int(
            raw_document["phasar-total-tracked-vars"]
        ) if "phasar-total-tracked-vars" in raw_document else None

        return BlameReportMetaData(
            num_functions, num_instructions, num_phasar_empty_tracked_vars,
            num_phasar_total_tracked_vars
        )


class BlameTaintScope(Enum):
    """The scope that was used for computing commit interactions."""
    REGION = 0
    COMMIT_IN_FUNCTION = 1
    COMMIT = 2

    @staticmethod
    def from_string(value: str) -> 'BlameTaintScope':
        return {
            "REGION": BlameTaintScope.REGION,
            "COMMIT_IN_FUNCTION": BlameTaintScope.COMMIT_IN_FUNCTION,
            "COMMIT": BlameTaintScope.COMMIT,
        }[value]


class BlameReport(BaseReport, shorthand="BR", file_type="yaml"):
    """Full blame report containing all blame interactions."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("BlameReport")
            version_header.raise_if_version_is_less_than(4)
            if version_header.version < 5:
                LOG.warning(
                    "You are using an outdated blame report format "
                    "that might not be supported in the future."
                )

            self.__meta_data = BlameReportMetaData \
                .create_blame_report_meta_data(next(documents))

            self.__function_entries: tp.Dict[str, BlameResultFunctionEntry] = {}
            raw_blame_report = next(documents)
            self.__blame_taint_scope = BlameTaintScope.from_string(
                # be backwards compatible with blame report version 4
                raw_blame_report.get('scope', "COMMIT")
            )
            for raw_func_entry in raw_blame_report['result-map']:
                new_function_entry = (
                    BlameResultFunctionEntry.create_blame_result_function_entry(
                        raw_func_entry,
                        raw_blame_report['result-map'][raw_func_entry]
                    )
                )
                self.__function_entries[new_function_entry.name
                                       ] = new_function_entry

    def get_blame_result_function_entry(
        self, mangled_function_name: str
    ) -> BlameResultFunctionEntry:
        """
        Get the result entry for a specific function.

        Args:
            mangled_function_name: mangled name of the function to look up
        """
        return self.__function_entries[mangled_function_name]

    @property
    def blame_taint_scope(self) -> BlameTaintScope:
        return self.__blame_taint_scope

    @property
    def function_entries(self) -> tp.ValuesView[BlameResultFunctionEntry]:
        """Iterate over all function entries."""
        return self.__function_entries.values()

    @property
    def head_commit(self) -> ShortCommitHash:
        """The current HEAD commit under which this CommitReport was created."""
        return self.filename.commit_hash

    @property
    def meta_data(self) -> BlameReportMetaData:
        """Access the meta data that was gathered with the ``BlameReport``."""
        return self.__meta_data

    def __str__(self) -> str:
        str_representation = ""
        for function in self.__function_entries.values():
            str_representation += str(function) + "\n"
        return str_representation


class BlameReportDiff():
    """Diff class that contains all interactions that changed between two report
    revisions."""

    def __init__(
        self, base_report: BlameReport, prev_report: BlameReport
    ) -> None:
        self.__function_entries: tp.Dict[str, BlameResultFunctionEntry] = {}
        self.__base_head = base_report.head_commit
        self.__prev_head = prev_report.head_commit
        self.__calc_diff_br(base_report, prev_report)
        if base_report.blame_taint_scope != prev_report.blame_taint_scope:
            raise AssertionError(
                "Cannot diff blame reports with different scopes."
            )
        self.__blame_taint_scope = base_report.blame_taint_scope

    @property
    def blame_taint_scope(self) -> BlameTaintScope:
        return self.__blame_taint_scope

    @property
    def base_head_commit(self) -> ShortCommitHash:
        return self.__base_head

    @property
    def prev_head_commit(self) -> ShortCommitHash:
        return self.__prev_head

    @property
    def function_entries(self) -> tp.ValuesView[BlameResultFunctionEntry]:
        """Iterate over all function entries in the diff."""
        return self.__function_entries.values()

    def get_blame_result_function_entry(
        self, mangled_function_name: str
    ) -> BlameResultFunctionEntry:
        """
        Get the result entry for a specific function in the diff.

        Args:
            mangled_function_name: mangled name of the function to look up
        """
        return self.__function_entries[mangled_function_name]

    def has_function(self, mangled_function_name: str) -> bool:
        return mangled_function_name in self.__function_entries

    def __calc_diff_br(
        self, base_report: BlameReport, prev_report: BlameReport
    ) -> None:
        function_names = {
            base_func_entry.name
            for base_func_entry in base_report.function_entries
        } | {
            prev_func_entry.name
            for prev_func_entry in prev_report.function_entries
        }
        for func_name in function_names:
            base_func_entry = None
            prev_func_entry = None
            try:
                base_func_entry = base_report.get_blame_result_function_entry(
                    func_name
                )
            except LookupError:
                pass

            try:
                prev_func_entry = prev_report.get_blame_result_function_entry(
                    func_name
                )
            except LookupError:
                pass

            # Only base report has the function
            if prev_func_entry is None and base_func_entry is not None:
                if base_func_entry.interactions:
                    self.__function_entries[func_name] = deepcopy(
                        base_func_entry
                    )

            # Only prev report has the function
            elif base_func_entry is None and prev_func_entry is not None:
                if prev_func_entry.interactions:
                    self.__function_entries[func_name] = deepcopy(
                        prev_func_entry
                    )

            # Both reports have the same function
            elif base_func_entry is not None and prev_func_entry is not None:
                diff_entry = _calc_diff_between_func_entries(
                    base_func_entry, prev_func_entry
                )

                if diff_entry.interactions:
                    self.__function_entries[func_name] = diff_entry

            else:
                raise AssertionError(
                    "The function name should be at least in one of the reports"
                )

    def __str__(self) -> str:
        str_representation = ""
        for function in self.__function_entries.values():
            str_representation += str(function) + "\n"
        return str_representation


ElementTy = tp.TypeVar('ElementTy')


def __count_elements(
    report: tp.Union[BlameReport, BlameReportDiff],
    get_elements_from_interaction: tp.Callable[[BlameInstInteractions],
                                               tp.Iterable[ElementTy]]
) -> int:
    elements: tp.Set[ElementTy] = set()

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            elements.update(get_elements_from_interaction(interaction))

    return len(elements)


def count_interactions(report: tp.Union[BlameReport, BlameReportDiff]) -> int:
    """
    Counts the number of interactions.

    Args:
        report: the blame report or diff

    Returns:
        the number of interactions in this report or diff
    """
    amount = 0

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            amount += abs(interaction.amount)

    return amount


def count_interacting_commits(
    report: tp.Union[BlameReport, BlameReportDiff],
) -> int:
    """
    Counts the number of unique interacting commits.

    Args:
        report: the blame report or diff

    Returns:
        the number unique interacting commits in this report or diff
    """
    return __count_elements(
        report, lambda interaction: interaction.interacting_taints
    )


def count_interacting_authors(
    report: tp.Union[BlameReport, BlameReportDiff],
    commit_lookup: CommitLookupTy
) -> int:
    """
    Counts the number of unique interacting authors.

    Args:
        report: the blame report or diff
        commit_lookup: function to look up commits

    Returns:
        the number unique interacting authors in this report or diff
    """

    def extract_interacting_authors(
        interaction: BlameInstInteractions
    ) -> tp.Iterable[str]:
        return map_commits(
            # Issue (se-sic/VaRA#647): improve author uniquifying
            lambda c: tp.cast(str, c.author.name),
            [btd.commit for btd in interaction.interacting_taints],
            commit_lookup
        )

    return __count_elements(report, extract_interacting_authors)


def generate_degree_tuples(
    report: tp.Union[BlameReport, BlameReportDiff]
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples (degree, amount) where degree is the interaction
    degree of a blame interaction, e.g., the number of incoming interactions,
    and amount is the number of times an interaction with this degree was found
    in the report.

    Args:
        report: the blame report

    Returns:
        list of tuples (degree, amount)
    """
    degree_dict: DegreeAmountMappingTy = defaultdict(int)

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            degree = len(interaction.interacting_taints)
            degree_dict[degree] += interaction.amount

    return list(degree_dict.items())


def gen_base_to_inter_commit_repo_pair_mapping(
    report: tp.Union[BlameReport, BlameReportDiff]
) -> tp.Dict[BlameTaintData, tp.Dict[BlameTaintData, int]]:
    """
    Maps the base CommitRepoPair of a blame interaction to each distinct
    interacting CommitRepoPair, which maps to the amount of the interaction.

    Args:
        report: blame report

    Returns:
        A mapping from base CommitRepoPairs to a mapping of the corresponding
        interacting CommitRepoPairs to their amount.
    """
    grouped_interactions: tp.Dict[BlameTaintData, tp.Dict[
        BlameTaintData, int]] = defaultdict(lambda: defaultdict(lambda: 0))

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            base_taint = interaction.base_taint

            for interacting_taint in interaction.interacting_taints:
                grouped_interactions[base_taint][interacting_taint
                                                ] += interaction.amount

    return grouped_interactions


DegreeAmountMappingTy = tp.Dict[int, int]


def generate_lib_dependent_degrees(
    report: tp.Union[BlameReport, BlameReportDiff]
) -> tp.Dict[str, tp.Dict[str, tp.List[tp.Tuple[int, int]]]]:
    """
    Args:
        report: blame report

    Returns:
        Map of tuples (degree, amount) categorised by their corresponding
        library name to their corresponding base library name.
    """

    base_inter_lib_degree_amount_mapping: tp.Dict[str, tp.Dict[
        str, DegreeAmountMappingTy]] = {}

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            base_repo_name = interaction.base_taint.commit.repository_name
            tmp_degree_of_libs: tp.Dict[str, int] = {}

            if base_repo_name not in base_inter_lib_degree_amount_mapping:
                base_inter_lib_degree_amount_mapping[base_repo_name] = {}

            for inter_taint in interaction.interacting_taints:
                inter_hash = inter_taint.commit
                inter_hash_repo_name = inter_hash.repository_name

                if (
                    inter_hash_repo_name
                    not in base_inter_lib_degree_amount_mapping[base_repo_name]
                ):
                    base_inter_lib_degree_amount_mapping[base_repo_name][
                        inter_hash_repo_name] = {}

                if inter_hash_repo_name not in tmp_degree_of_libs:
                    tmp_degree_of_libs[inter_hash_repo_name] = 1
                else:
                    tmp_degree_of_libs[inter_hash_repo_name] += 1

            for repo_name, degree in tmp_degree_of_libs.items():
                if (
                    degree
                    not in base_inter_lib_degree_amount_mapping[base_repo_name]
                    [repo_name]
                ):
                    base_inter_lib_degree_amount_mapping[base_repo_name][
                        repo_name][degree] = 0

                base_inter_lib_degree_amount_mapping[base_repo_name][repo_name][
                    degree] += interaction.amount

    # Transform to tuples (degree, amount)
    result_dict: tp.Dict[str, tp.Dict[str, tp.List[tp.Tuple[int, int]]]] = {}
    for base_name, inter_lib_dict in base_inter_lib_degree_amount_mapping.items(
    ):
        result_dict[base_name] = {}
        for inter_lib_name, degree_amount_dict in inter_lib_dict.items():
            result_dict[base_name][inter_lib_name] = list(
                degree_amount_dict.items()
            )

    return result_dict


def generate_author_degree_tuples(
    report: tp.Union[BlameReport, BlameReportDiff],
    commit_lookup: CommitLookupTy
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples (author_degree, amount) where author_degree is
    the number of unique authors for all blame interaction, e.g., the number of
    unique authors of incoming interactions, and amount is the number of times
    an interaction with this degree was found in the report.

    Args:
        report: the blame report
        commit_lookup: function to look up commits

    Returns:
        list of tuples (author_degree, amount)
    """

    degree_dict: tp.DefaultDict[int, int] = defaultdict(int)

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            author_list = map_commits(
                # Issue (se-sic/VaRA#647): improve author uniquifying
                lambda c: tp.cast(str, c.author.name),
                [btd.commit for btd in interaction.interacting_taints],
                commit_lookup
            )

            degree = len(set(author_list))
            degree_dict[degree] += interaction.amount

    return list(degree_dict.items())


def generate_time_delta_distribution_tuples(
    report: tp.Union[BlameReport, BlameReportDiff],
    commit_lookup: CommitLookupTy, bucket_size: int,
    aggregate_function: tp.Callable[[tp.Sequence[tp.Union[int, float]]],
                                    tp.Union[int, float]]
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples that represent the distribution of time delta
    interactions. The first value in the tuple represents the degree of the time
    delta, bucketed according to ``bucket_size``. The second value is the time
    delta, aggregated over all interacting commits by the passed
    ``aggregate_function``.

    Args:
        report: to analyze
        commit_lookup: function to look up commits
        bucket_size: size of a time bucket in days
        aggregate_function: to aggregate the delta values of all
                            interacting commits

    Returns:
        list of (degree, amount) tuples
    """
    degree_dict: tp.DefaultDict[int, int] = defaultdict(int)

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            base_crp: CommitRepoPair = interaction.base_taint.commit
            if base_crp.commit_hash == UNCOMMITTED_COMMIT_HASH:
                continue

            base_commit = commit_lookup(interaction.base_taint.commit)
            base_c_time = datetime.utcfromtimestamp(base_commit.commit_time)

            def translate_to_time_deltas2(
                commit: pygit2.Commit,
                base_time: datetime = base_c_time
            ) -> int:
                other_c_time = datetime.utcfromtimestamp(commit.commit_time)
                return abs((base_time - other_c_time).days)

            author_list = map_commits(
                translate_to_time_deltas2,
                [btd.commit for btd in interaction.interacting_taints],
                commit_lookup
            )

            degree = aggregate_function(author_list) if author_list else 0
            bucket = round(degree / bucket_size)
            degree_dict[bucket] += interaction.amount

    return list(degree_dict.items())


def generate_avg_time_distribution_tuples(
    report: tp.Union[BlameReport, BlameReportDiff],
    commit_lookup: CommitLookupTy, bucket_size: int
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples that represent the distribution of average time
    delta interactions. The first value in the tuple represents the degree of
    the time delta, bucketed according to ``bucket_size``. The second value is
    the time delta, averaged over all interacting commits.

    Args:
        report: to analyze
        commit_lookup: function to look up commits
        bucket_size: size of a time bucket in days

    Returns:
        list of (degree, avg_time) tuples
    """
    return generate_time_delta_distribution_tuples(
        report, commit_lookup, bucket_size, np.average
    )


def generate_max_time_distribution_tuples(
    report: tp.Union[BlameReport, BlameReportDiff],
    commit_lookup: CommitLookupTy, bucket_size: int
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples that represent the distribution of maximal time
    delta interactions. The first value in the tuple represents the degree of
    the time delta, bucketed according to ``bucket_size``. The second value is
    the max time delta, i.e., the maximal time distance between the base commit
    and one of the all interacting commits.

    Args:
        report: to analyze
        commit_lookup: function to look up commits
        bucket_size: size of a time bucket in days

    Returns:
        list of (degree, max_time) tuples
    """
    return generate_time_delta_distribution_tuples(
        report, commit_lookup, bucket_size, max
    )


def generate_in_head_interactions(
    report: BlameReport
) -> tp.List[BlameInstInteractions]:
    """
    Generate a list of interactions where the base_hash of the interaction is
    the same as the HEAD of the report.

    Args:
        report: BlameReport to get the interactions from
    """
    head_interactions = []
    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            if interaction.base_taint.commit.commit_hash.startswith(
                report.head_commit
            ):
                head_interactions.append(interaction)
                continue

    return head_interactions


def generate_out_head_interactions(
    report: BlameReport
) -> tp.List[BlameInstInteractions]:
    """
    Generate a list of interactions where one of the interacting hashes is the
    same as the HEAD of the report.

    Args:
        report: BlameReport to get the interactions from
    """
    head_interactions = []
    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            for interacting_taint in interaction.interacting_taints:
                if interacting_taint.commit.commit_hash.startswith(
                    report.head_commit
                ):
                    head_interactions.append(interaction)
                    break
    return head_interactions


def get_interacting_commits_for_commit(
    report: BlameReport, commit: CommitRepoPair
) -> tp.Tuple[tp.Set[CommitRepoPair], tp.Set[CommitRepoPair]]:
    """
    Get all commits a given commits interacts with separated by incoming and
    outgoing interactions.

    Args:
        report: BlameReport to get the interactions from
        commit: commit to get the interacting commits for

    Returns:
        two sets for the interacting commits seperated by incoming and outgoing
        interactions
    """
    in_commits: tp.Set[CommitRepoPair] = set()
    out_commits: tp.Set[CommitRepoPair] = set()
    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            interacting_commits = [
                taint.commit for taint in interaction.interacting_taints
            ]
            if commit == interaction.base_taint.commit:
                out_commits.update(interacting_commits)
            if commit in interacting_commits:
                in_commits.add(interaction.base_taint.commit)

    return in_commits, out_commits
