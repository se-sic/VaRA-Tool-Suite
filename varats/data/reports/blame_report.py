"""
Module for BlameReport, a collection of blame interactions.
"""

import typing as tp
from pathlib import Path
from collections import defaultdict
import yaml

import pygit2

from varats.data.report import BaseReport, MetaReport, FileStatusExtension
from varats.data.version_header import VersionHeader
from varats.utils.project_util import get_local_project_git


class BlameInstInteractions():
    """
    An interaction between a base commit, attached to an instruction, and
    other commits. For the blame analysis, these commits stem from data flows
    into the instruction.
    """

    def __init__(self, raw_inst_entry: tp.Dict[str, tp.Any]) -> None:
        self.__base_hash = str(raw_inst_entry['base-hash'])
        self.__interacting_hashes: tp.List[str] = []
        for raw_inst_hash in raw_inst_entry['interacting-hashes']:
            self.__interacting_hashes.append(str(raw_inst_hash))
        self.__amount = int(raw_inst_entry['amount'])

    @property
    def base_hash(self) -> str:
        """
        Base hash of the analyzed instruction.
        """
        return self.__base_hash

    @property
    def interacting_hashes(self) -> tp.List[str]:
        """
        List of hashes that interact with the base.
        """
        return self.__interacting_hashes

    @property
    def amount(self) -> int:
        """
        Number of same interactions found in this function.
        """
        return self.__amount

    def __str__(self) -> str:
        str_representation = "{base_hash} <-(# {amount:4})- [".format(
            base_hash=self.base_hash, amount=self.amount)
        sep = ""
        for interacting_hash in self.interacting_hashes:
            str_representation += sep + interacting_hash
            sep = ", "
        str_representation += "]\n"
        return str_representation


class BlameResultFunctionEntry():
    """
    Collection of all interactions for a specific function.
    """

    def __init__(self, name: str,
                 raw_function_entry: tp.Dict[str, tp.Any]) -> None:
        self.__name = name
        self.__demangled_name = str(raw_function_entry['demangled-name'])
        self.__inst_list: tp.List[BlameInstInteractions] = []
        for raw_inst_entry in raw_function_entry['insts']:
            self.__inst_list.append(BlameInstInteractions(raw_inst_entry))

    @property
    def name(self) -> str:
        """
        Name of the function. The name is manged for C++ code, either with
        the itanium or windows mangling schema.
        """
        return self.__name

    @property
    def demangled_name(self) -> str:
        """
        Demangled name of the function.
        """
        return self.__demangled_name

    @property
    def interactions(self) -> tp.List[BlameInstInteractions]:
        """
        List of found instruction blame-interactions.
        """
        return self.__inst_list

    def __str__(self) -> str:
        str_representation = "{name} ({demangled_name})\n".format(
            name=self.name, demangled_name=self.demangled_name)
        for inst in self.__inst_list:
            str_representation += "  - {}".format(inst)
        return str_representation


class BlameReport(BaseReport):
    """
    Full blame report containing all blame interactions.
    """

    SHORTHAND = "BR"
    FILE_TYPE = "yaml"

    def __init__(self, path: Path) -> None:
        super(BlameReport, self).__init__()
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
                new_function_entry = BlameResultFunctionEntry(
                    raw_func_entry,
                    raw_blame_report['result-map'][raw_func_entry])
                self.__function_entries[
                    new_function_entry.name] = new_function_entry

    @property
    def path(self) -> Path:
        """
        Path to the report file.
        """
        return self.__path

    def get_blame_result_function_entry(self, mangled_function_name: str
                                       ) -> BlameResultFunctionEntry:
        """
        Get the result entry for a specific function.
        """
        return self.__function_entries[mangled_function_name]

    @property
    def function_entries(self) -> tp.ValuesView[BlameResultFunctionEntry]:
        """
        Iterate over all function entries.
        """
        return self.__function_entries.values()

    @property
    def head_commit(self) -> str:
        """
        The current HEAD commit under which this CommitReport was created.
        """
        return BlameReport.get_commit_hash_from_result_file(self.path.name)

    @staticmethod
    def get_file_name(project_name: str,
                      binary_name: str,
                      project_version: str,
                      project_uuid: str,
                      extension_type: FileStatusExtension,
                      file_ext: str = "yaml") -> str:
        """
        Generates a filename for a commit report with 'yaml'
        as file extension.
        """
        return MetaReport.get_file_name(BlameReport.SHORTHAND, project_name,
                                        binary_name, project_version,
                                        project_uuid, extension_type, file_ext)

    def __str__(self) -> str:
        str_representation = ""
        for function in self.__function_entries.values():
            str_representation += str(function) + "\n"
        return str_representation


def generate_degree_tuples(report: BlameReport) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples (degree, amount) where degree is the interaction
    degree of a blame interaction, e.g., the number of incoming interactions,
    and amount is the number of times an interaction with this degree was
    found in the report.
    """
    degree_dict: tp.DefaultDict[int, int] = defaultdict(int)

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            degree = len(interaction.interacting_hashes)
            degree_dict[degree] += interaction.amount

    return [(k, v) for k, v in degree_dict.items()]


def generate_author_degree_tuples(
        report: BlameReport,
        project_name: str,
) -> tp.List[tp.Tuple[int, int]]:
    """
    Generates a list of tuples (author_degree, amount) where author_degree is
    the number of unique authors for all blame interaction, e.g., the number of
    unique authors of incoming interactions, and amount is the number of times
    an interaction with this degree was found in the report.
    """

    def translate_to_authors(hash_list: tp.List[str],
                             get_commit: tp.Callable[[str], pygit2.Commit]
                            ) -> tp.List[str]:
        author_list = []
        for c_hash in hash_list:
            commit = get_commit(c_hash)
            if commit is None:
                if c_hash == "0000000000000000000000000000000000000000":
                    print("Project {project} was analyzed with uncommited ".
                          format(project=project_name) +
                          "changes, ignoring changes in analysis.")
                else:
                    raise LookupError(
                        "Could not find commit {commit} in {project}".format(
                            commit=c_hash, project=project_name))
            else:
                author_list.append(commit.author.name)
        return author_list

    degree_dict: tp.DefaultDict[int, int] = defaultdict(int)
    cache_dict: tp.Dict[str, pygit2.Commit] = {}

    repo = get_local_project_git(project_name)

    def get_commit(c_hash: str) -> pygit2.Commit:
        if c_hash in cache_dict:
            return cache_dict[c_hash]

        commit = repo.get(c_hash)
        cache_dict[c_hash] = commit
        return commit

    for func_entry in report.function_entries:
        for interaction in func_entry.interactions:
            author_list = translate_to_authors(interaction.interacting_hashes,
                                               get_commit)
            degree = len(set(author_list))
            degree_dict[degree] += interaction.amount

    return [(k, v) for k, v in degree_dict.items()]


