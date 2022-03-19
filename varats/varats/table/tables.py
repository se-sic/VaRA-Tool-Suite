"""General tables module."""
import abc
import logging
import sys
import typing as tp
from copy import deepcopy
from enum import Enum
from pathlib import Path

import click

from varats.paper_mgmt.artefacts import Artefact, ArtefactFileInfo
from varats.ts_utils.artefact_util import (
    CaseStudyConverter,
    ReportTypeConverter,
)
from varats.ts_utils.cli_util import (
    make_cli_option,
    add_cli_options,
    CLIOptionTy,
    cli_yn_choice,
    convert_value,
    CLIOptionWithConverter,
)
from varats.ts_utils.click_param_types import (
    create_single_case_study_choice,
    create_multi_case_study_choice,
    create_report_type_choice,
    EnumChoice,
)
from varats.utils.settings import vara_cfg

if sys.version_info <= (3, 8):
    from typing_extensions import Protocol, runtime_checkable, final
else:
    from typing import Protocol, runtime_checkable, final

if tp.TYPE_CHECKING:
    from varats.table import table  # pylint: disable=unused-import

LOG = logging.getLogger(__name__)


class TableFormat(Enum):
    """List of supported TableFormats."""
    value: str

    PLAIN = "plain"
    SIMPLE = "simple"
    GITHUB = "github"
    GRID = "grid"
    FANCY_GRID = "fancy_grid"
    PIPE = "pipe"
    ORGTBL = "orgtbl"
    JIRA = "jira"
    PRESTO = "presto"
    PRETTY = "pretty"
    PSQL = "psql"
    RST = "rst"
    MEDIAWIKI = "mediawiki"
    MOINMOIN = "moinmoin"
    YOUTRACK = "youtrack"
    HTML = "html"
    UNSAFEHTML = "unsafehtml"
    LATEX = "latex"
    LATEX_RAW = "latex_raw"
    LATEX_BOOKTABS = "latex_booktabs"
    TEXTILE = "textile"


class CommonTableOptions():
    """
    Options common to all tables.

    These options are handled by the :class:`TableGenerator` base class
    and are
    not passed down to specific table generators.

    Args:
        view: if `True`, view the table instead of writing it to a file
        table_dir: directory to write tables to
                  (relative to config value 'tables/table_dir')
        file_type: the file type for the written table file
        dry_run: if ``True``, do not generate any files
    """

    def __init__(
        self, view: bool, table_dir: Path, file_type: str, wrap_table: bool,
        dry_run: bool
    ):
        self.view = view
        # Will be overridden when generating artefacts
        self.table_base_dir = Path(str(vara_cfg()['tables']['table_dir']))
        self.table_dir = table_dir
        self.file_type = file_type
        self.wrapt_table = wrap_table
        self.dry_run = dry_run

    @staticmethod
    def from_kwargs(**kwargs: tp.Any) -> 'CommonTableOptions':
        """Construct a ``CommonTableOptions`` object from a kwargs dict."""
        return CommonTableOptions(
            kwargs.get("view", False), Path(kwargs.get("table_dir", ".")),
            kwargs.get("file_type", "tex"), kwargs.get("wrap_table", False),
            kwargs.get("dry_run", False)
        )

    __options = [
        make_cli_option(
            "-v",
            "--view",
            is_flag=True,
            help="View the table instead of saving it to a file."
        ),
        make_cli_option(
            "--file-type",
            type=click.Choice(["txt", "md", "html", "tex", "rst"]),
            default="tex",
            help="File type for the table."
        ),
        make_cli_option(
            "--table-dir",
            type=click.Path(path_type=Path),
            default=Path("."),
            help="Set the directory the tables will be written to "
            "(relative to config value 'tables/table_dir')."
        ),
        make_cli_option(
            "--wrap-table",
            type=bool,
            default=False,
            help="Wrap tables inside a complete latex document."
        ),
        make_cli_option(
            "--dry-run",
            is_flag=True,
            help="Only log tables that would be generated but do not "
            "generate."
            "Useful for debugging table generators."
        ),
    ]

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        """
        Decorate a command with common table CLI options.

        This function can be used as a decorator.

        Args:
            command: the command to decorate

        Returns:
            the decorated command
        """
        return add_cli_options(command, *cls.__options)

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        """
        Create a dict representation for this object.

        It holds that
        ``options == CommonTableOptions.from_kwargs(**options.get_dict())``.

        Returns:
            a dict representation of this object
        """
        return {
            "view": self.view,
            "file_type": self.file_type,
            "table_dir": self.table_dir,
            "dry_run": self.dry_run
        }


OptionType = tp.TypeVar("OptionType")


class TableConfigOption(tp.Generic[OptionType]):
    """
    Class representing a table config option.

    Values can be retrieved via the call operator.

    Args:
        name: name of the option
        help_str: help string for this option
        default: global default value for the option
        view_default: global default value when in view mode; do not pass if
                      same value is required in both modes
        value: user-provided value of the option; do not pass if not set by user
    """

    def __init__(
        self,
        name: str,
        help_str: str,
        default: OptionType,
        view_default: tp.Optional[OptionType] = None,
        value: tp.Optional[OptionType] = None
    ) -> None:
        self.__name = name
        self.__metavar = name.upper()
        self.__type = type(default)
        self.__default = default
        self.__view_default = view_default
        self.__value: tp.Optional[OptionType] = value
        self.__help = f"{help_str} (global default = {default})"

    @property
    def name(self) -> str:
        return self.__name

    @property
    def default(self) -> OptionType:
        return self.__default

    @property
    def view_default(self) -> tp.Optional[OptionType]:
        return self.__view_default

    @property
    def value(self) -> tp.Optional[OptionType]:
        return self.__value

    def with_value(self, value: OptionType) -> 'TableConfigOption[OptionType]':
        """
        Create a copy of this option with the given value.

        Args:
            value: the value for the copied option

        Returns:
            a copy of the option with the given value
        """
        return TableConfigOption(
            self.name, self.__help, self.__default, self.__view_default, value
        )

    def to_cli_option(self) -> CLIOptionTy:
        """
        Create a CLI option from this option.

        Returns:
            a CLI option for this option
        """
        if self.__type is bool:
            return make_cli_option(
                f"--{self.__name.replace('_', '-')}",
                is_flag=True,
                required=False,
                help=self.__help
            )
        return make_cli_option(
            f"--{self.__name.replace('_', '-')}",
            metavar=self.__metavar,
            type=self.__type,
            required=False,
            help=self.__help
        )

    def value_or_default(
        self,
        view: bool,
        default: tp.Optional[OptionType] = None,
        view_default: tp.Optional[OptionType] = None
    ) -> OptionType:
        """
        Retrieve the value for this option.

        The precedence for values is
        `user provided value > table-specific default > global default`.

        This function can also be called via the call operator.

        Args:
            view: whether view-mode is enabled
            default: table-specific default value
            view_default: table-specific default value when in view-mode

        Returns:
            the value for this option
        """
        # cannot pass view_default if option has no default for view mode
        assert not (view_default and not self.__view_default)

        if self.value:
            return self.value
        if view:
            if self.__view_default:
                return view_default or self.__view_default
            return default or self.__default
        return default or self.__default

    def __str__(self) -> str:
        return f"{self.__name}[default={self.__default}, value={self.value}]"


@runtime_checkable
class PCOGetter(Protocol[OptionType]):
    """Getter type for options with no view default."""

    def __call__(self, default: tp.Optional[OptionType] = None) -> OptionType:
        ...


@runtime_checkable
class PCOGetterV(Protocol[OptionType]):
    """Getter type for options with view default."""

    def __call__(
        self,
        default: tp.Optional[OptionType] = None,
        view_default: tp.Optional[OptionType] = None
    ) -> OptionType:
        ...


class TableConfig():
    """
    Class with parameters that influence a table's appearance.

    Instances should typically be created with the :func:`from_kwargs` function.
    """

    def __init__(self, view: bool, *options: TableConfigOption[tp.Any]) -> None:
        self.__view = view
        self.__options = deepcopy(self._option_decls)
        for option in options:
            self.__options[option.name] = option

    _option_decls: tp.Dict[str, TableConfigOption[tp.Any]] = {
        decl.name: decl for decl in tp.cast(
            tp.List[TableConfigOption[tp.Any]], [
                TableConfigOption(
                    "font_size",
                    default=10,
                    view_default=10,
                    help_str="The font size of the table."
                ),
                TableConfigOption(
                    "fig_title", default="", help_str="The title of the table."
                ),
                TableConfigOption(
                    "line_width",
                    default=0.25,
                    view_default=1,
                    help_str="The width of the table line(s)."
                )
            ]
        )
    }

    def __option_getter(
        self, option: TableConfigOption[OptionType]
    ) -> PCOGetter[OptionType]:
        """Creates a getter for options with no view default."""

        def get_value(default: tp.Optional[OptionType] = None) -> OptionType:
            return option.value_or_default(self.__view, default)

        return get_value

    def __option_getter_v(
        self, option: TableConfigOption[OptionType]
    ) -> PCOGetterV[OptionType]:
        """Creates a getter for options with view default."""

        def get_value(
            default: tp.Optional[OptionType] = None,
            view_default: tp.Optional[OptionType] = None
        ) -> OptionType:
            return option.value_or_default(self.__view, default, view_default)

        return get_value

    @property
    def fig_title(self) -> PCOGetter[str]:
        return self.__option_getter(self.__options["fig_title"])

    @property
    def font_size(self) -> PCOGetterV[int]:
        return self.__option_getter_v(self.__options["font_size"])

    @property
    def line_width(self) -> PCOGetterV[float]:
        return self.__option_getter_v(self.__options["line_width"])

    @classmethod
    def from_kwargs(cls, view: bool, **kwargs: tp.Any) -> 'TableConfig':
        """
        Instantiate a ``TableConfig`` object with values from the given kwargs.

        Args:
            **kwargs: a dict containing values to be used by this config

        Returns:
            a table config object with values from the kwargs
        """
        return TableConfig(
            view, *[
                option_decl.with_value(kwargs[option_decl.name])
                for option_decl in cls._option_decls.values()
                if option_decl.name in kwargs
            ]
        )

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        """
        Decorate a command with table config CLI options.

        This function can be used as a decorator.

        Args:
            command: the command to decorate

        Returns:
            the decorated command
        """
        return add_cli_options(
            command,
            *[option.to_cli_option() for option in cls._option_decls.values()]
        )

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        """
        Create a dict representation from this table config.

        The dict only contains options for which values were explicitly set.
        It holds that ``config == TableConfig.from_kwargs(**config.get_dict())``.

        Returns:
            a dict representation of this table config
        """
        return {
            option.name: option.value
            for option in self.__options.values()
            if option.value
        }


REQUIRE_CASE_STUDY: CLIOptionTy = convert_value(
    "case_study", CaseStudyConverter
)(
    make_cli_option(
        "-cs",
        "--case-study",
        type=create_single_case_study_choice(),
        required=True,
        metavar="NAME",
        help="The case study to use for the table."
    )
)
REQUIRE_MULTI_CASE_STUDY: CLIOptionTy = convert_value(
    "case_study", CaseStudyConverter
)(
    make_cli_option(
        "-cs",
        "--case-study",
        type=create_multi_case_study_choice(),
        required=True,
        metavar="NAMES",
        help="The case study to use for the table."
    )
)
REQUIRE_REVISION: CLIOptionTy = make_cli_option(
    "-rev",
    "--revision",
    type=str,
    required=True,
    metavar="SHORT_COMMIT_HASH",
    help="The revision to use for the table."
)
OPTIONAL_REPORT_TYPE: CLIOptionTy = convert_value(
    "report_type", ReportTypeConverter
)(
    make_cli_option(
        "--report-type",
        type=create_report_type_choice(),
        required=False,
        help="The report type to use for the table."
    )
)
OPTIONAL_TABLE_FORMAT: CLIOptionTy = make_cli_option(
    "--format",
    type=EnumChoice(TableFormat, case_sensitive=False),
    default=TableFormat.SIMPLE,
    required=False,
    help="The format of the table."
)


class TableGeneratorFailed(Exception):
    """Exception for table generator related errors."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class TableGenerator(abc.ABC):
    """
    Superclass for all table generators.

    A table generator is responsible for generating one or more tables.
    Subclasses are automatically registered if they reside in the
    ``varats.tables`` package and must override the function
    :meth:`generate` so that it returns one or more table instances that should
    be generated.
    The generation itself (i.e., saving or displaying tables) is handled by the
    `call` operator (which should not be overridden!).

    Creating a table generator class requires to provide additional parameters
    in the class definition, e.g.::

        class MyTableGenerator(
            TableGenerator,
            table_name="my_generator",  # table generator name as shown by CLI
            options=[]  # put CLI option declarations here
        ):
            ...
    """

    GENERATORS: tp.Dict[str, tp.Type['TableGenerator']] = {}
    """Registry for concrete table generators."""

    NAME: str
    """Name of the concrete generator class (set automatically)."""

    OPTIONS: tp.List[CLIOptionTy]
    """Table generator CLI Options (set automatically)."""

    def __init__(self, table_config: TableConfig, **table_kwargs: tp.Any):
        self.__table_config = table_config
        self.__table_kwargs = table_kwargs

    @classmethod
    def __init_subclass__(
        cls, generator_name: str, options: tp.List[CLIOptionTy],
        **kwargs: tp.Any
    ) -> None:
        """
        Register concrete table generators.

        Args:
            generator_name: table generator name as shown by the CLI
            table:          table class used by the generator
            options:        command line options needed by the generator
        """
        super().__init_subclass__(**kwargs)
        cls.NAME = generator_name
        cls.OPTIONS = options
        cls.GENERATORS[generator_name] = cls

    @staticmethod
    def get_table_generator_types_help_string() -> str:
        """
        Generates help string for visualizing all available tables.

        Returns:
            a help string that contains all available table names.
        """
        return "The following table generators are available:\n  " + "\n  ".join(
            list(TableGenerator.GENERATORS)
        )

    @staticmethod
    def get_class_for_table_generator_type(
        table_generator_type_name: str
    ) -> tp.Type['TableGenerator']:
        """
        Get the class for table from the table registry.

        Args:
            table_generator_type_name: name of the table generator

        Returns:
            the class for the table generator
        """
        if table_generator_type_name not in TableGenerator.GENERATORS:
            raise LookupError(
                f"Unknown table generator '{table_generator_type_name}'.\n" +
                TableGenerator.get_table_generator_types_help_string()
            )

        table_cls = TableGenerator.GENERATORS[table_generator_type_name]
        return table_cls

    @property
    def table_config(self) -> TableConfig:
        """Options that influence a table's appearance."""
        return self.__table_config

    @property
    def table_kwargs(self) -> tp.Dict[str, tp.Any]:
        """Table-specific options."""
        return self.__table_kwargs

    @abc.abstractmethod
    def generate(self) -> tp.List['varats.table.table.Table']:
        """Create the table instance(s) that should be generated."""

    @final
    def __call__(self, common_options: CommonTableOptions) -> None:
        """
        Generate the tables as specified by this generator.

        Args:
            common_options: common options to use for the table(s)
        """
        table_dir = common_options.table_base_dir / common_options.table_dir
        if not table_dir.exists():
            table_dir.mkdir(parents=True)

        tables = self.generate()

        if len(tables) > 1 and common_options.view:
            common_options.view = cli_yn_choice(
                f"Do you really want to view all {len(tables)} tables? "
                f"If you answer 'no', the tables will still be generated.", "n"
            )

        for table in tables:
            if common_options.dry_run:
                LOG.info(repr(table))
                continue

            if common_options.view:
                table.show()
            else:
                # TODO: rename wrap_document to wrap_table
                table.save(
                    table_dir,
                    wrap_document=common_options.wrapt_table,
                    filetype=common_options.file_type
                )


def _convert_kwargs(
    table_generator_type: tp.Type[TableGenerator],
    table_kwargs: tp.Dict[str, tp.Any],
    to_string: bool = False
) -> tp.Dict[str, tp.Any]:
    """
    Apply conversions to kwargs as specified by table generator CLI options.

    Args:
        table_generator_type: table generator with CLI option/converter
                             declarations
        table_kwargs: table kwargs as values or strings
        to_string: if ``True`` convert to string, otherwise convert to value

    Returns:
        the kwargs with applied conversions
    """
    converter = {
        decl_converter.name: decl_converter.converter for decl_converter in [
            tp.cast(CLIOptionWithConverter[tp.Any], cli_decl)
            for cli_decl in table_generator_type.OPTIONS
            if isinstance(cli_decl, CLIOptionWithConverter)
        ]
    }
    kwargs: tp.Dict[str, tp.Any] = {}
    for key, value in table_kwargs.items():
        if key in converter.keys():
            if to_string:
                kwargs[key] = converter[key].value_to_string(value)
            else:
                kwargs[key] = converter[key].string_to_value(value)
        else:
            kwargs[key] = value
    return kwargs


class TableArtefact(Artefact, artefact_type="table", artefact_type_version=1):
    """
    An artefact defining a :class:`table<varats.tables.table.Table>`.

    Args:
        name: name of this artefact
        output_dir: output dir relative to config value
                    'artefacts/artefacts_dir'
        table_generator_type: the
                    :attr:`type of table<varats.table.tables.TableGenerator>`
                    to use
        kwargs: additional arguments that will be passed to the table class
    """

    def __init__(
        self, name: str, output_dir: Path, table_generator_type: str,
        common_options: CommonTableOptions, table_config: TableConfig,
        **kwargs: tp.Any
    ) -> None:
        super().__init__(name, output_dir)
        self.__table_generator_type = table_generator_type
        self.__table_type_class = TableGenerator.get_class_for_table_generator_type(
            self.__table_generator_type
        )
        self.__common_options = common_options
        self.__common_options.table_base_dir = Artefact.base_output_dir()
        self.__common_options.table_dir = output_dir
        self.__table_config = table_config
        self.__table_kwargs = kwargs

    @property
    def table_generator_type(self) -> str:
        """The type of table generator used to generate this artefact."""
        return self.__table_generator_type

    @property
    def table_generator_class(self) -> tp.Type[TableGenerator]:
        """The class associated with :func:`table_generator_type`."""
        return self.__table_type_class

    @property
    def common_options(self) -> CommonTableOptions:
        """Options that are available to all tables."""
        return self.__common_options

    @property
    def table_config(self) -> TableConfig:
        """Options that influence the visual representation of a table."""
        return self.__table_config

    @property
    def table_kwargs(self) -> tp.Any:
        """Additional arguments that will be passed to the table."""
        return self.__table_kwargs

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        """
        Create a dict representation for this object.

        Returns:
            a dict representation of this object
        """
        artefact_dict = super().get_dict()
        artefact_dict['table_generator'] = self.__table_generator_type
        artefact_dict['table_config'] = self.__table_config.get_dict()
        artefact_dict = {
            **self.__common_options.get_dict(),
            **_convert_kwargs(
                self.table_generator_class, self.__table_kwargs, to_string=True
            ),
            **artefact_dict
        }
        artefact_dict.pop("table_dir")  # duplicate of Artefact's output_path
        return artefact_dict

    @staticmethod
    def create_artefact(
        name: str, output_dir: Path, **kwargs: tp.Any
    ) -> 'Artefact':
        """
        Create an artefact instance from the given information.

        Args:
            name: the name of the artefact
            output_dir: the output directory for the artefact
            **kwargs: artefact-specific arguments

        Returns:
            an artefact instance
        """
        table_generator_type = kwargs.pop('table_generator')
        common_options = CommonTableOptions.from_kwargs(**kwargs)
        table_config = TableConfig.from_kwargs(
            common_options.view, **kwargs.pop("table_config", {})
        )
        return TableArtefact(
            name, output_dir, table_generator_type, common_options,
            table_config,
            **_convert_kwargs(
                TableGenerator.
                get_class_for_table_generator_type(table_generator_type),
                kwargs,
                to_string=False
            )
        )

    @staticmethod
    def from_generator(
        name: str, generator: TableGenerator, common_options: CommonTableOptions
    ) -> 'TableArtefact':
        """
        Create a table artefact from a generator.

        Args:
            name: name for the artefact
            generator: generator class to use for the artefact
            common_options: common table options

        Returns:
            an instantiated table artefact
        """
        return TableArtefact(
            name, common_options.table_dir, generator.NAME, common_options,
            generator.table_config, **generator.table_kwargs
        )

    def generate_artefact(self) -> None:
        """Generate the specified table(s)."""
        generator_instance = self.table_generator_class(
            self.table_config, **self.__table_kwargs
        )
        generator_instance(self.common_options)

    def get_artefact_file_infos(self) -> tp.List[ArtefactFileInfo]:
        """
        Retrieve information about files generated by this artefact.

        Returns:
            a list of file info objects
        """
        generator_instance = self.table_generator_class(
            self.table_config, **self.__table_kwargs
        )
        return [
            ArtefactFileInfo(
                table.table_file_name(self.common_options.file_type),
                table.table_kwargs.get("case_study", None)
            ) for table in generator_instance.generate()
        ]
