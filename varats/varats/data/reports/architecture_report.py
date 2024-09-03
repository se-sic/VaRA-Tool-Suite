"""Architecture report implementation."""

from pathlib import Path

from varats.report.report import BaseReport


class ArchitectureReport(BaseReport, shorthand="AR", file_type="txt"):
    """An metadata report for analyzing a project's architecture."""

    # TODO Implement the ArchitectureReport class.


class ArchitectureTaintResultFunctionEntry:

    def __init__(
        self, name: str, demangled_name: str, file_name: str,
        interactions: tp.Dict[str, int]
    ) -> None:
        self.__name = name
        self.__demangled_name = demangled_name
        self.__file_name = file_name
        self.__insts = interactions

    @staticmethod
    def create_architecture_taint_result_function_entry(
        name: str, raw_function_entry: tp.Dict[str, tp.Any]
    ):
        demangled_name = str(raw_function_entry['demangled-name'])
        file_name = str(raw_function_entry.get('file'))
        interactions = raw_function_entry['IncomingRegions']
        return ArchitectureTaintResultFunctionEntry(
            name, demangled_name, file_name, interactions
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
    def file_name(self) -> tp.Optional[str]:
        """Name of file containing the function if available."""
        return self.__file_name

    @property
    def interactions(self) -> tp.Dict[str, int]:
        """List of found instruction blame-interactions."""
        return self.__insts

    def __str__(self) -> str:
        str_representation = f"{self.name} ({self.demangled_name})\n"
        for region, amount in self.__inst.items():
            str_representation += f"  - {region}: {amount}\n"
        return str_representation


class ArchitectureTaintReport(BaseReport, shorthand="ATR", file_type="yaml"):

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(path, 'r') as stream:
            documents = yaml.load_all(stream, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("ArchitectureTaintReport")

            self.__function_entries: tp.Dict[
                str, ArchitectureTaintResultFunctionEntry] = {}
            raw_architecture_taint_report = next(documents)
            for raw_func_entry in raw_architecture_taint_report['result-map']:
                new_function_entry = (
                    ArchitectureTaintResultFunctionEntry.
                    create_architecture_taint_result_function_entry(
                        raw_func_entry,
                        raw_architecture_taint_report['result-map']
                        [raw_func_entry]
                    )
                )
                self.__function_entries[new_function_entry.name
                                       ] = new_function_entry

    def get_architecture_taint_result_function_entry(
        self, mangled_function_name: str
    ) -> tp.Optional[ArchitectureTaintResultFunctionEntry]:
        """
        Get the result entry for a specific function.

        Args:
            mangled_function_name: mangled name of the function to look up
        """
        return self.__function_entries.get(mangled_function_name)

    @property
    def function_entries(
        self
    ) -> tp.Dict[str, ArchitectureTaintResultFunctionEntry]:
        """List of found function blame-interactions."""
        return self.__function_entries

    def __str__(self) -> str:
        str_representation = ""
        for func_entry in self.__function_entries.values():
            str_representation += str(func_entry) + "\n"
        return str_representation
