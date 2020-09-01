"""Base table module."""

import abc
import typing as tp
from enum import Enum
from pathlib import Path

from varats.tables.tables import TableRegistry


class TableFormat(Enum):
    """List of supported TableFormats."""

    plain = "plain"
    simple = "simple"
    github = "github"
    grid = "grid"
    fancy_grid = "fancy_grid"
    pipe = "pipe"
    orgtbl = "orgtbl"
    jira = "jira"
    presto = "presto"
    pretty = "pretty"
    psql = "psql"
    rst = "rst"
    mediawiki = "mediawiki"
    moinmoin = "moinmoin"
    youtrack = "youtrack"
    html = "html"
    unsafehtml = "unsafehtml"
    latex = "latex"
    latex_raw = "latex_raw"
    latex_booktabs = "latex_booktabs"
    textile = "textile"


class Table(metaclass=TableRegistry):
    """An abstract base class for all tables generated by VaRA-TS."""

    format_filetypes = {
        TableFormat.github: "md",
        TableFormat.html: "html",
        TableFormat.unsafehtml: "html",
        TableFormat.latex: "tex",
        TableFormat.latex_raw: "tex",
        TableFormat.latex_booktabs: "tex",
        TableFormat.rst: "rst",
    }

    def __init__(self, name: str, **kwargs: tp.Any) -> None:
        self.__name = name
        self.__format = TableFormat.latex_booktabs
        self.__saved_extra_args = kwargs

    @property
    def name(self) -> str:
        """
        Name of the current table.

        Test:
        >>> Table('test').name
        'test'
        """
        return self.__name

    @property
    def format(self) -> TableFormat:
        """
        Current table format as used by python-tabulate.

        Test:
        >>> Table('test').format
        <TableFormat.latex_booktabs: 'latex_booktabs'>
        """
        return self.__format

    @format.setter
    def format(self, new_format: TableFormat) -> None:
        """
        Set current format of the table.

        Args:
            new_format: a table format as used by python-tabulate
        """
        self.__format = new_format

    @property
    def table_kwargs(self) -> tp.Any:
        """
        Access the kwargs passed to the initial table.

        Test:
        >>> tab = Table('test', foo='bar', baz='bazzer')
        >>> tab.table_kwargs['foo']
        'bar'
        >>> tab.table_kwargs['baz']
        'bazzer'
        """
        return self.__saved_extra_args

    @abc.abstractmethod
    def tabulate(self) -> str:
        """Build the table using tabulate."""

    def save(
        self,
        path: tp.Optional[Path] = None,
    ) -> None:
        """
        Save the current table to a file.

        Args:
            path: The path where the file is stored (excluding the file name).
            file_name: the file name of the table; this overrides automatic
                       file name construction.
        """
        filetype = self.format_filetypes.get(self.__format, "txt")

        if path is None:
            table_dir = Path(self.table_kwargs["table_dir"])
        else:
            table_dir = path

        project_name = self.table_kwargs["project"]
        stages = 'S' if self.table_kwargs['sep_stages'] else ''
        file_name = f"{project_name}_{self.name}{stages}"

        table = self.tabulate()
        with open(table_dir / f"{file_name}.{filetype}", "w") as outfile:
            outfile.write(table)
