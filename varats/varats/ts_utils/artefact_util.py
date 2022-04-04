"""Utility functions for working with artefacts."""
import sys
import typing as tp

from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.report.report import BaseReport
from varats.ts_utils.cli_util import (
    CLIOptionConverter,
    CLIOptionTy,
    make_cli_option,
    CLIOptionWithConverter,
)

if sys.version_info <= (3, 8):
    from typing_extensions import Protocol, runtime_checkable
else:
    from typing import Protocol, runtime_checkable

if tp.TYPE_CHECKING:
    # pylint: disable=unused-import
    from varats.plot.plots import PlotGenerator
    # pylint: disable=unused-import
    from varats.table.tables import TableGenerator


class CaseStudyConverter(CLIOptionConverter[CaseStudy]):
    """CLI option converter for case studies."""

    @staticmethod
    def value_to_string(
        value: tp.Union[CaseStudy, tp.List[CaseStudy]]
    ) -> tp.Union[str, tp.List[str]]:
        if isinstance(value, tp.List):
            pc = get_loaded_paper_config()
            if value == pc.get_all_case_studies():
                return "all"
            return [f"{cs.project_name}_{cs.version}" for cs in value]
        return f"{value.project_name}_{value.version}"

    @staticmethod
    def string_to_value(
        str_value: tp.Union[str, tp.List[str]]
    ) -> tp.Union[CaseStudy, tp.List[CaseStudy]]:
        pc = get_loaded_paper_config()
        if isinstance(str_value, tp.List):
            return [
                cs for cs_name in str_value
                for cs in pc.get_case_studies(cs_name)
            ]
        if str_value == "all":
            return pc.get_all_case_studies()
        return pc.get_case_studies(str_value)[0]


class ReportTypeConverter(CLIOptionConverter[tp.Type[BaseReport]]):
    """CLI option converter for case studies."""

    @staticmethod
    def value_to_string(
        value: tp.Union[tp.Type[BaseReport], tp.List[tp.Type[BaseReport]]]
    ) -> tp.Union[str, tp.List[str]]:
        if isinstance(value, tp.List):
            raise ValueError("Conversion for lists not implemented.")
        return value.__name__

    @staticmethod
    def string_to_value(
        str_value: tp.Union[str, tp.List[str]]
    ) -> tp.Union[tp.Type[BaseReport], tp.List[tp.Type[BaseReport]]]:
        if isinstance(str_value, tp.List):
            raise ValueError("Conversion for lists not implemented.")
        return BaseReport.REPORT_TYPES[str_value]


GeneratorTy = tp.TypeVar(
    "GeneratorTy", tp.Type['PlotGenerator'], tp.Type['TableGenerator']
)


def convert_kwargs(
    table_generator_type: GeneratorTy,
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


# Plot/Table config options
OptionType = tp.TypeVar("OptionType")


class ConfigOption(tp.Generic[OptionType]):
    """
    Class representing a plot/table config option.

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

    def with_value(self, value: OptionType) -> 'ConfigOption[OptionType]':
        """
        Create a copy of this option with the given value.

        Args:
            value: the value for the copied option

        Returns:
            a copy of the option with the given value
        """
        return ConfigOption(
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
        `user provided value > plot-specific default > global default`.

        This function can also be called via the call operator.

        Args:
            view: whether view-mode is enabled
            default: plot-specific default value
            view_default: plot-specific default value when in view-mode

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
class COGetter(Protocol[OptionType]):
    """Getter type for options with no view default."""

    def __call__(self, default: tp.Optional[OptionType] = None) -> OptionType:
        ...


@runtime_checkable
class COGetterV(Protocol[OptionType]):
    """Getter type for options with view default."""

    def __call__(
        self,
        default: tp.Optional[OptionType] = None,
        view_default: tp.Optional[OptionType] = None
    ) -> OptionType:
        ...
