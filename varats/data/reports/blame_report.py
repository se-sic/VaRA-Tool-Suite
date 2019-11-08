"""
Module for BlameReport, a collection of blame interactions.
"""

import typing as tp
from pathlib import Path
import yaml

from varats.data.report import BaseReport, FileStatusExtension
from varats.data.version_header import VersionHeader


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

            self.__function_entries: tp.Dict[
                str, BlameResultFunctionEntry] = dict()
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
        return BaseReport.get_file_name(BlameReport.SHORTHAND, project_name,
                                        binary_name, project_version,
                                        project_uuid, extension_type, file_ext)

    def __str__(self) -> str:
        str_representation = ""
        for function in self.__function_entries.values():
            str_representation += str(function) + "\n"
        return str_representation
