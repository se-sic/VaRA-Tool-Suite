"""Module for BlameReport, a collection of blame interactions."""

import typing as tp
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import numpy as np
import pygit2
import yaml

from varats.data.report import BaseReport, FileStatusExtension, MetaReport
from varats.data.version_header import VersionHeader
from varats.utils.git_util import create_commit_lookup_helper, map_commits


class BlameInstInteractions():
    """
    An interaction between a base commit, attached to an instruction, and other
    commits.

    For the blame analysis, these commits stem from data flows into the
    instruction.
    """

    def __init__(
        self, base_hash: str, interacting_hashes: tp.List[str], amount: int
    ) -> None:
        self.__base_hash = base_hash
        self.__interacting_hashes = interacting_hashes
        self.__amount = amount

    @staticmethod
    def create_blame_inst_interactions(
        raw_inst_entry: tp.Dict[str, tp.Any]
    ) -> 'BlameInstInteractions':
        """Creates a `BlameInstInteractions` entry from the corresponding yaml
        document section."""
        base_hash = str(raw_inst_entry['base-hash'])
        interacting_hashes: tp.List[str] = []
        for raw_inst_hash in raw_inst_entry['interacting-hashes']:
            interacting_hashes.append(str(raw_inst_hash))
        amount = int(raw_inst_entry['amount'])
        return BlameInstInteractions(base_hash, interacting_hashes, amount)

    @property
    def base_commit(self) -> str:
        """Base hash of the analyzed instruction."""
        return self.__base_hash

    @property
    def interacting_commits(self) -> tp.List[str]:
        """List of hashes that interact with the base."""
        return self.__interacting_hashes

    @property
    def amount(self) -> int:
        """Number of same interactions found in this function."""
        return self.__amount

    def __str__(self) -> str:
        str_representation = "{base_hash} <-(# {amount:4})- [".format(
            base_hash=self.base_commit, amount=self.amount
        )
        sep = ""
        for interacting_commit in self.interacting_commits:
            str_representation += sep + interacting_commit
            sep = ", "
        str_representation += "]\n"
        return str_representation

    def __eq__(self, other: tp.Any) -> bool:
        if isinstance(other, BlameInstInteractions):
            if self.base_commit == other.base_commit:
                return sorted(self.interacting_commits
                             ) == sorted(other.interacting_commits)

        return False

    def __lt__(self, other: tp.Any) -> bool:
        if isinstance(other, BlameInstInteractions):
            if self.base_commit < other.base_commit:
                return True
            return sorted(self.interacting_commits
                         ) < sorted(other.interacting_commits)

        return False


class BlameResultFunctionEntry():
    """Collection of all interactions for a specific function."""

    def __init__(
        self, name: str, demangled_name: str,
        blame_insts: tp.List[BlameInstInteractions]
    ) -> None:
        self.__name = name
        self.__demangled_name = demangled_name
        self.__inst_list = blame_insts

    @staticmethod
    def create_blame_result_function_entry(
        name: str, raw_function_entry: tp.Dict[str, tp.Any]
    ) -> 'BlameResultFunctionEntry':
        """Creates a `BlameResultFunctionEntry` from the corresponding yaml
        document section."""
        demangled_name = str(raw_function_entry['demangled-name'])
        inst_list: tp.List[BlameInstInteractions] = []
        for raw_inst_entry in raw_function_entry['insts']:
            inst_list.append(
                BlameInstInteractions.
                create_blame_inst_interactions(raw_inst_entry)
            )
        return BlameResultFunctionEntry(name, demangled_name, inst_list)

    @property
    def name(self) -> str:
        """
        Name of the function.

        The name is manged for C++ code, either with the itanium or windows
        mangling schema.
        """
        return self.__name

    @property
    def demangled_name(self) -> str:
        """Demangled name of the function."""
        return self.__demangled_name

    @property
    def interactions(self) -> tp.List[BlameInstInteractions]:
        """List of found instruction blame-interactions."""
        return self.__inst_list

    def __str__(self) -> str:
        str_representation = "{name} ({demangled_name})\n".format(
            name=self.name, demangled_name=self.demangled_name
        )
        for inst in self.__inst_list:
            str_representation += "  - {}".format(inst)
        return str_representation


def _calc_diff_between_func_entries(
    base_func_entry: BlameResultFunctionEntry,
    prev_func_entry: BlameResultFunctionEntry
) -> BlameResultFunctionEntry:
    diff_interactions: tp.List[BlameInstInteractions] = []

    base_interactions = sorted(base_func_entry.interactions)
    prev_interactions = sorted(prev_func_entry.interactions)

    for base_inter in base_interactions:
        if base_inter in prev_interactions:
            prev_inter_idx = prev_interactions.index(base_inter)
            prev_inter = prev_interactions.pop(prev_inter_idx)
            # create new blame inst interaction with the absolute differente
            # between base and prev
            difference = base_inter.amount - prev_inter.amount
            if difference != 0:
                diff_interactions.append(
                    BlameInstInteractions(
                        base_inter.base_commit,
                        deepcopy(base_inter.interacting_commits), difference
                    )
                )
        else:
            # append new interaction from base report
            diff_interactions.append(deepcopy(base_inter))

    # append left over interactions from previous blame report
    diff_interactions += prev_interactions

    return BlameResultFunctionEntry(
        base_func_entry.name, base_func_entry.demangled_name, diff_interactions
    )


class BlameReport(BaseReport):
    """Full blame report containing all blame interactions."""

    SHORTHAND = "BR"
    FILE_TYPE = "yaml"

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__path = path
        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("BlameReport")
            version_header.raise_if_version_is_less_than(1)

            self.__function_entries: tp.Dict[str,
                                             BlameResultFunctionEntry] = dict()
            raw_blame_report = next(documents)
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
    def function_entries(self) -> tp.ValuesView[BlameResultFunctionEntry]:
        """Iterate over all function entries."""
        return self.__function_entries.values()

    @property
    def head_commit(self) -> str:
        """The current HEAD commit under which this CommitReport was created."""
        return BlameReport.get_commit_hash_from_result_file(self.path.name)

    @staticmethod
    def get_file_name(
        project_name: str,
        binary_name: str,
        project_version: str,
        project_uuid: str,
        extension_type: FileStatusExtension,
        file_ext: str = "yaml"
    ) -> str:
        """
        Generates a filename for a commit report with 'yaml' as file extension.

        Args:
            project_name: name of the project for which the report was generated
            binary_name: name of the binary for which the report was generated
            project_version: version of the analyzed project, i.e., commit hash
            project_uuid: benchbuild uuid for the experiment run
            extension_type: to specify the status of the generated report
            file_ext: file extension of the report file

        Returns:
            name for the report file that can later be uniquly identified
        """
        return MetaReport.get_file_name(
            BlameReport.SHORTHAND, project_name, binary_name, project_version,
            project_uuid, extension_type, file_ext
        )

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
        self.__function_entries: tp.Dict[str, BlameResultFunctionEntry] = dict()
        self.__base_head = base_report.head_commit
        self.__prev_head = prev_report.head_commit
        self.__calc_diff_br(base_report, prev_report)

    @property
    def base_head_commit(self) -> str:
        return self.__base_head

    @property
    def prev_head_commit(self) -> str:
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


ElementType = tp.TypeVar('ElementType')


def __count_elements(
    report: tp.Union[BlameReport, BlameReportDiff],
    get_elements_from_interaction: tp.Callable[[BlameInstInteractions],
                                               tp.Iterable[ElementType]]
) -> int:
    elements: tp.Set[ElementType] = set()

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
        report, lambda interaction: interaction.interacting_commits
    )


def count_interacting_authors(
    report: tp.Union[BlameReport, BlameReportDiff],
    project_name: str,
) -> int:
    """
    Counts the number of unique interacting authors.

    Args:
        report: the blame report or diff
        project_name: name of the project the report is based on

    Returns:
        the number unique interacting authors in this report or diff
    """

    commit_lookup = create_commit_lookup_helper(project_name)

    def extract_interacting_authors(
        interaction: BlameInstInteractions
    ) -> tp.Iterable[str]:
        return map_commits(
            # Issue (se-passau/VaRA#647): improve author uniquifying
            lambda c: tp.cast(str, c.author.name),
            interaction.interacting_commits,
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
    degree_dict: tp.DefaultDict[int, int] = defaultdict(int)

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            degree = len(interaction.interacting_commits)
            degree_dict[degree] += interaction.amount

    return list(degree_dict.items())


def generate_author_degree_tuples(
    report: tp.Union[BlameReport, BlameReportDiff],
    project_name: str,
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples (author_degree, amount) where author_degree is
    the number of unique authors for all blame interaction, e.g., the number of
    unique authors of incoming interactions, and amount is the number of times
    an interaction with this degree was found in the report.

    Args:
        report: the blame report
        project_name: name of the project the report is based on

    Returns:
        list of tuples (author_degree, amount)
    """

    degree_dict: tp.DefaultDict[int, int] = defaultdict(int)
    commit_lookup = create_commit_lookup_helper(project_name)

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            author_list = map_commits(
                # Issue (se-passau/VaRA#647): improve author uniquifying
                lambda c: tp.cast(str, c.author.name),
                interaction.interacting_commits,
                commit_lookup
            )

            degree = len(set(author_list))
            degree_dict[degree] += interaction.amount

    return list(degree_dict.items())


def generate_time_delta_distribution_tuples(
    report: tp.Union[BlameReport,
                     BlameReportDiff], project_name: str, bucket_size: int,
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
        project_name: name of the project
        bucket_size: size of a time bucket in days
        aggregate_function: to aggregate the delta values of all
                            interacting commits

    Returns:
        list of (degree, amount) tuples
    """
    degree_dict: tp.DefaultDict[int, int] = defaultdict(int)
    commit_lookup = create_commit_lookup_helper(project_name)

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            if (
                interaction.base_commit ==
                "0000000000000000000000000000000000000000"
            ):
                continue

            base_commit = commit_lookup(interaction.base_commit)
            base_c_time = datetime.utcfromtimestamp(base_commit.commit_time)

            def translate_to_time_deltas2(
                commit: pygit2.Commit,
                base_time: datetime = base_c_time
            ) -> int:
                other_c_time = datetime.utcfromtimestamp(commit.commit_time)
                return abs((base_time - other_c_time).days)

            author_list = map_commits(
                translate_to_time_deltas2, interaction.interacting_commits,
                commit_lookup
            )

            degree = aggregate_function(author_list) if author_list else 0
            bucket = round(degree / bucket_size)
            degree_dict[bucket] += interaction.amount

    return list(degree_dict.items())


def generate_avg_time_distribution_tuples(
    report: tp.Union[BlameReport, BlameReportDiff], project_name: str,
    bucket_size: int
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples that represent the distribution of average time
    delta interactions. The first value in the tuple represents the degree of
    the time delta, bucketed according to ``bucket_size``. The second value is
    the time delta, averaged over all interacting commits.

    Args:
        report: to analyze
        project_name: name of the project
        bucket_size: size of a time bucket in days

    Returns:
        list of (degree, avg_time) tuples
    """
    return generate_time_delta_distribution_tuples(
        report, project_name, bucket_size, np.average
    )


def generate_max_time_distribution_tuples(
    report: tp.Union[BlameReport, BlameReportDiff], project_name: str,
    bucket_size: int
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples that represent the distribution of maximal time
    delta interactions. The first value in the tuple represents the degree of
    the time delta, bucketed according to ``bucket_size``. The second value is
    the max time delta, i.e., the maximal time distance between the base commit
    and one of the all interacting commits.

    Args:
        report: to analyze
        project_name: name of the project
        bucket_size: size of a time bucket in days

    Returns:
        list of (degree, max_time) tuples
    """
    return generate_time_delta_distribution_tuples(
        report, project_name, bucket_size, max
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
            if interaction.base_commit.startswith(report.head_commit):
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
            for interacting_commit in interaction.interacting_commits:
                if interacting_commit.startswith(report.head_commit):
                    head_interactions.append(interaction)
                    break
    return head_interactions
