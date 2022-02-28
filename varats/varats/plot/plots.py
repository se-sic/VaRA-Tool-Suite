"""General plots module."""
import abc
import logging
import sys
import typing as tp
from copy import deepcopy
from pathlib import Path

import click

from varats.paper_mgmt.artefacts import Artefact, ArtefactFileInfo
from varats.ts_utils.artefact_util import (
    CaseStudyConverter,
    ReportTypeConverter,
)
from varats.ts_utils.cli_util import (
    make_cli_option,
    CLIOptionTy,
    add_cli_options,
    cli_yn_choice,
    CLIOptionConverter,
    CLIOptionWithConverter,
    convert_value,
)
from varats.ts_utils.click_param_types import (
    create_multi_case_study_choice,
    create_single_case_study_choice,
    create_report_type_choice,
)
from varats.utils.settings import vara_cfg

if sys.version_info <= (3, 8):
    from typing_extensions import Protocol, runtime_checkable, final
else:
    from typing import Protocol, runtime_checkable, final

if tp.TYPE_CHECKING:
    import varats.plot.plot  # pylint: disable=W0611

LOG = logging.getLogger(__name__)


class CommonPlotOptions():
    """
    Options common to all plots.

    These options are handled by the :class:`PlotGenerator` base class and are
    not passed down to specific plot generators.

    Args:
        view: if `True`, view the plot instead of writing it to a file
        plot_dir: directory to write plots to
                  (relative to config value 'plots/plot_dir')
        file_type: the file type for the written plot file
        dry_run: if ``True``, do not generate any files
    """

    def __init__(
        self, view: bool, plot_dir: Path, file_type: str, dry_run: bool
    ):
        self.view = view
        # Will be overridden when generating artefacts
        self.plot_base_dir = Path(str(vara_cfg()['plots']['plot_dir']))
        self.plot_dir = plot_dir
        self.file_type = file_type
        self.dry_run = dry_run

    @staticmethod
    def from_kwargs(**kwargs: tp.Any) -> 'CommonPlotOptions':
        """Construct a ``CommonPlotOptions`` object from a kwargs dict."""
        return CommonPlotOptions(
            kwargs.get("view", False), Path(kwargs.get("plot_dir", ".")),
            kwargs.get("file_type", "svg"), kwargs.get("dry_run", False)
        )

    __options = [
        make_cli_option(
            "-v",
            "--view",
            is_flag=True,
            help="View the plot instead of saving it to a file."
        ),
        make_cli_option(
            "--file-type",
            type=click.Choice(["png", "svg", "pdf"]),
            default="svg",
            help="File type for the plot."
        ),
        make_cli_option(
            "--plot-dir",
            type=click.Path(path_type=Path),
            default=Path("."),
            help="Set the directory the plots will be written to "
            "(relative to config value 'plots/plot_dir')."
        ),
        make_cli_option(
            "--dry-run",
            is_flag=True,
            help="Only log plots that would be generated but do not generate."
            "Useful for debugging plot generators."
        ),
    ]

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        """
        Decorate a command with common plot CLI options.

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
        ``options == CommonPlotOptions.from_kwargs(**options.get_dict())``.

        Returns:
            a dict representation of this object
        """
        return {
            "view": self.view,
            "file_type": self.file_type,
            "plot_dir": self.plot_dir,
            "dry_run": self.dry_run
        }


OptionType = tp.TypeVar("OptionType")


class PlotConfigOption(tp.Generic[OptionType]):
    """
    Class representing a plot config option.

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

    def with_value(self, value: OptionType) -> 'PlotConfigOption[OptionType]':
        """
        Create a copy of this option with the given value.

        Args:
            value: the value for the copied option

        Returns:
            a copy of the option with the given value
        """
        return PlotConfigOption(
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


class PlotConfig():
    """
    Class with parameters that influence a plot's appearance.

    Instances should typically be created with the :func:`from_kwargs` function.
    """

    def __init__(self, view: bool, *options: PlotConfigOption[tp.Any]) -> None:
        self.__view = view
        self.__options = deepcopy(self._option_decls)
        for option in options:
            self.__options[option.name] = option

    _option_decls: tp.Dict[str, PlotConfigOption[tp.Any]] = {
        decl.name: decl for decl in tp.cast(
            tp.List[PlotConfigOption[tp.Any]], [
                PlotConfigOption(
                    "style",
                    default="classic",
                    help_str="Matplotlib style to use."
                ),
                PlotConfigOption(
                    "fig_title",
                    default="",
                    help_str="The title of the plot figure."
                ),
                PlotConfigOption(
                    "font_size",
                    default=10,
                    view_default=10,
                    help_str="The font size of the plot figure."
                ),
                PlotConfigOption(
                    "width",
                    default=1500,
                    view_default=1500,
                    help_str="The width of the resulting plot file."
                ),
                PlotConfigOption(
                    "height",
                    default=1000,
                    view_default=1000,
                    help_str="The height of the resulting plot file."
                ),
                PlotConfigOption(
                    "legend_title",
                    default="",
                    help_str="The title of the legend."
                ),
                PlotConfigOption(
                    "legend_size",
                    default=2,
                    view_default=8,
                    help_str="The size of the legend."
                ),
                PlotConfigOption(
                    "show_legend",
                    default=False,
                    help_str="If present, show the legend."
                ),
                PlotConfigOption(
                    "line_width",
                    default=0.25,
                    view_default=1,
                    help_str="The width of the plot line(s)."
                ),
                PlotConfigOption(
                    "x_tick_size",
                    default=2,
                    view_default=10,
                    help_str="The size of the x-ticks."
                ),
                PlotConfigOption(
                    "label_size",
                    default=2,
                    view_default=2,
                    help_str="The label size of CVE/bug annotations."
                ),
                PlotConfigOption(
                    "dpi", default=1200, help_str="The dpi of the plot."
                )
            ]
        )
    }

    def __option_getter(
        self, option: PlotConfigOption[OptionType]
    ) -> PCOGetter[OptionType]:
        """Creates a getter for options with no view default."""

        def get_value(default: tp.Optional[OptionType] = None) -> OptionType:
            return option.value_or_default(self.__view, default)

        return get_value

    def __option_getter_v(
        self, option: PlotConfigOption[OptionType]
    ) -> PCOGetterV[OptionType]:
        """Creates a getter for options with view default."""

        def get_value(
            default: tp.Optional[OptionType] = None,
            view_default: tp.Optional[OptionType] = None
        ) -> OptionType:
            return option.value_or_default(self.__view, default, view_default)

        return get_value

    @property
    def style(self) -> PCOGetter[str]:
        return self.__option_getter(self.__options["style"])

    @property
    def fig_title(self) -> PCOGetter[str]:
        return self.__option_getter(self.__options["fig_title"])

    @property
    def font_size(self) -> PCOGetterV[int]:
        return self.__option_getter_v(self.__options["font_size"])

    @property
    def width(self) -> PCOGetterV[int]:
        return self.__option_getter_v(self.__options["width"])

    @property
    def height(self) -> PCOGetterV[int]:
        return self.__option_getter_v(self.__options["height"])

    @property
    def legend_title(self) -> PCOGetter[str]:
        return self.__option_getter(self.__options["legend_title"])

    @property
    def legend_size(self) -> PCOGetterV[int]:
        return self.__option_getter_v(self.__options["legend_size"])

    @property
    def show_legend(self) -> PCOGetter[bool]:
        return self.__option_getter(self.__options["show_legend"])

    @property
    def line_width(self) -> PCOGetterV[float]:
        return self.__option_getter_v(self.__options["line_width"])

    @property
    def x_tick_size(self) -> PCOGetterV[int]:
        return self.__option_getter_v(self.__options["x_tick_size"])

    @property
    def label_size(self) -> PCOGetterV[int]:
        return self.__option_getter_v(self.__options["label_size"])

    @property
    def dpi(self) -> PCOGetter[int]:
        return self.__option_getter(self.__options["dpi"])

    @classmethod
    def from_kwargs(cls, view: bool, **kwargs: tp.Any) -> 'PlotConfig':
        """
        Instantiate a ``PlotConfig`` object with values from the given kwargs.

        Args:
            **kwargs: a dict containing values to be used by this config

        Returns:
            a plot config object with values from the kwargs
        """
        return PlotConfig(
            view, *[
                option_decl.with_value(kwargs[option_decl.name])
                for option_decl in cls._option_decls.values()
                if option_decl.name in kwargs
            ]
        )

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        """
        Decorate a command with plot config CLI options.

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
        Create a dict representation from this plot config.

        The dict only contains options for which values were explicitly set.
        It holds that ``config == PlotConfig.from_kwargs(**config.get_dict())``.

        Returns:
            a dict representation of this plot config
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
        help="The case study to use for the plot."
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
        help="The case study to use for the plot."
    )
)
REQUIRE_REVISION: CLIOptionTy = make_cli_option(
    "-rev",
    "--revision",
    type=str,
    required=True,
    metavar="SHORT_COMMIT_HASH",
    help="The revision to use for the plot."
)
REQUIRE_REPORT_TYPE: CLIOptionTy = convert_value(
    "report_type", ReportTypeConverter
)(
    make_cli_option(
        "--report-type",
        type=create_report_type_choice(),
        required=True,
        help="The report type to use for the plot."
    )
)


class PlotGeneratorFailed(Exception):
    """Exception for plot generator related errors."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class PlotGenerator(abc.ABC):
    """
    Superclass for all plot generators.

    A plot generator is responsible for generating one or more plots.
    Subclasses are automatically registered if they reside in the
    ``varats.plots`` package and must override the function
    :meth:`generate` so that it returns one or more plot instances that should
    be generated.
    The generation itself (i.e., saving or displaying plots) is handeled by the
    `call` operator (which should not be overridden!).

    Creating a plot generator class requires to provide additional parameters in
    the class definition, e.g.::

        class MyPlotGenerator(
            PlotGenerator,
            plot_name="my_generator",  # plot generator name as shown by CLI
            options=[]  # put CLI option declarations here
        ):
            ...
    """

    GENERATORS: tp.Dict[str, tp.Type['PlotGenerator']] = {}
    """Registry for concrete plot generators."""

    NAME: str
    """Name of the concrete generator class (set automatically)."""

    OPTIONS: tp.List[CLIOptionTy]
    """Plot generator CLI Options (set automatically)."""

    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        self.__plot_config = plot_config
        self.__plot_kwargs = plot_kwargs

    @classmethod
    def __init_subclass__(
        cls, generator_name: str, options: tp.List[CLIOptionTy],
        **kwargs: tp.Any
    ) -> None:
        """
        Register concrete plot generators.

        Args:
            generator_name: plot generator name as shown by the CLI
            plot:           plot class used by the generator
            options:        command line options needed by the generator
        """
        super().__init_subclass__(**kwargs)
        cls.NAME = generator_name
        cls.OPTIONS = options
        cls.GENERATORS[generator_name] = cls

    @staticmethod
    def get_plot_generator_types_help_string() -> str:
        """
        Generates help string for visualizing all available plots.

        Returns:
            a help string that contains all available plot names.
        """
        return "The following plot generators are available:\n  " + "\n  ".join(
            list(PlotGenerator.GENERATORS)
        )

    @staticmethod
    def get_class_for_plot_generator_type(
        plot_generator_type_name: str
    ) -> tp.Type['PlotGenerator']:
        """
        Get the class for plot from the plot registry.

        Args:
            plot_generator_type_name: name of the plot generator

        Returns:
            the class for the plot generator
        """
        if plot_generator_type_name not in PlotGenerator.GENERATORS:
            raise LookupError(
                f"Unknown plot generator '{plot_generator_type_name}'.\n" +
                PlotGenerator.get_plot_generator_types_help_string()
            )

        plot_cls = PlotGenerator.GENERATORS[plot_generator_type_name]
        return plot_cls

    @property
    def plot_config(self) -> PlotConfig:
        """Options that influence a plot's appearance."""
        return self.__plot_config

    @property
    def plot_kwargs(self) -> tp.Dict[str, tp.Any]:
        """Plot-specific options."""
        return self.__plot_kwargs

    @abc.abstractmethod
    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        """Create the plot instance(s) that should be generated."""

    @final
    def __call__(self, common_options: CommonPlotOptions) -> None:
        """
        Generate the plots as specified by this generator.

        Args:
            common_options: common options to use for the plot(s)
        """
        plot_dir = common_options.plot_base_dir / common_options.plot_dir
        if not plot_dir.exists():
            plot_dir.mkdir(parents=True)

        plots = self.generate()

        if len(plots) > 1 and common_options.view:
            common_options.view = cli_yn_choice(
                f"Do you really want to view all {len(plots)} plots? "
                f"If you answer 'no', the plots will still be generated.", "n"
            )

        for plot in plots:
            if common_options.dry_run:
                LOG.info(repr(plot))
                continue

            if common_options.view:
                plot.show()
            else:
                plot.save(plot_dir, filetype=common_options.file_type)


def _convert_kwargs(
    plot_generator_type: tp.Type[PlotGenerator],
    plot_kwargs: tp.Dict[str, tp.Any],
    to_string: bool = False
) -> tp.Dict[str, tp.Any]:
    """
    Apply conversions to kwargs as specified by plot generator CLI options.

    Args:
        plot_generator_type: plot generator with CLI option/converter
                             declarations
        plot_kwargs: plot kwargs as values or strings
        to_string: if ``True`` convert to string, otherwise convert to value

    Returns:
        the kwargs with applied conversions
    """
    converter = {
        decl_converter.name: decl_converter.converter for decl_converter in [
            tp.cast(CLIOptionWithConverter[tp.Any], cli_decl)
            for cli_decl in plot_generator_type.OPTIONS
            if isinstance(cli_decl, CLIOptionWithConverter)
        ]
    }
    kwargs: tp.Dict[str, tp.Any] = {}
    for key, value in plot_kwargs.items():
        if key in converter.keys():
            if to_string:
                kwargs[key] = converter[key].value_to_string(value)
            else:
                kwargs[key] = converter[key].string_to_value(value)
        else:
            kwargs[key] = value
    return kwargs


class PlotArtefact(Artefact, artefact_type="plot", artefact_type_version=2):
    """
    An artefact defining a :class:`~varats.plot.plot.Plot`.

    Args:
        name: name of this artefact
        output_dir: output dir relative to config value
                    'artefacts/artefacts_dir'
        plot_generator_type: the
                    :attr:`type of plot<varats.plot.plots.PlotGenerator>`
                    to use
        file_format: the file format of the generated plot
        kwargs: additional arguments that will be passed to the plot class
    """

    def __init__(
        self, name: str, output_dir: Path, plot_generator_type: str,
        common_options: CommonPlotOptions, plot_config: PlotConfig,
        **kwargs: tp.Any
    ) -> None:
        super().__init__(name, output_dir)
        self.__plot_generator_type = plot_generator_type
        self.__plot_type_class = \
            PlotGenerator.get_class_for_plot_generator_type(
            self.__plot_generator_type
        )
        self.__common_options = common_options
        self.__common_options.plot_base_dir = Artefact.base_output_dir()
        self.__common_options.plot_dir = output_dir
        self.__plot_config = plot_config
        self.__plot_kwargs = kwargs

    @property
    def plot_generator_type(self) -> str:
        """The type of plot generator used to generate this artefact."""
        return self.__plot_generator_type

    @property
    def plot_generator_class(self) -> tp.Type[PlotGenerator]:
        """The class associated with :func:`plot_generator_type`."""
        return self.__plot_type_class

    @property
    def common_options(self) -> CommonPlotOptions:
        """Options that are available to all plots."""
        return self.__common_options

    @property
    def plot_config(self) -> PlotConfig:
        """Options that influence the visual representation of a plot."""
        return self.__plot_config

    @property
    def plot_kwargs(self) -> tp.Any:
        """Additional arguments that will be passed to the plot."""
        return self.__plot_kwargs

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        """
        Create a dict representation for this object.

        Returns:
            a dict representation of this object
        """
        artefact_dict = super().get_dict()
        artefact_dict['plot_generator'] = self.__plot_generator_type
        artefact_dict['plot_config'] = self.__plot_config.get_dict()
        artefact_dict = {
            **self.__common_options.get_dict(),
            **_convert_kwargs(
                self.plot_generator_class, self.__plot_kwargs, to_string=True
            ),
            **artefact_dict
        }
        artefact_dict.pop("plot_dir")  # duplicate of Artefact's output_path
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
        plot_generator_type = kwargs.pop('plot_generator')
        common_options = CommonPlotOptions.from_kwargs(**kwargs)
        plot_config = PlotConfig.from_kwargs(
            common_options.view, **kwargs.pop("plot_config", {})
        )
        return PlotArtefact(
            name, output_dir, plot_generator_type, common_options, plot_config,
            **_convert_kwargs(
                PlotGenerator.
                get_class_for_plot_generator_type(plot_generator_type),
                kwargs,
                to_string=False
            )
        )

    @staticmethod
    def from_generator(
        name: str, generator: PlotGenerator, common_options: CommonPlotOptions
    ) -> 'PlotArtefact':
        """
        Create a plot artefact from a generator.

        Args:
            name: name for the artefact
            generator: generator class to use for the artefact
            common_options: common plot options

        Returns:
            an instantiated plot artefact
        """
        return PlotArtefact(
            name, common_options.plot_dir, generator.NAME, common_options,
            generator.plot_config, **generator.plot_kwargs
        )

    def generate_artefact(self) -> None:
        """Generate the specified plot(s)."""
        generator_instance = self.plot_generator_class(
            self.plot_config, **self.__plot_kwargs
        )
        generator_instance(self.common_options)

    def get_artefact_file_infos(self) -> tp.List[ArtefactFileInfo]:
        """
        Retrieve information about files generated by this artefact.

        Returns:
            a list of file info objects
        """
        generator_instance = self.plot_generator_class(
            self.plot_config, **self.__plot_kwargs
        )
        return [
            ArtefactFileInfo(
                plot.plot_file_name(self.common_options.file_type),
                plot.plot_kwargs.get("case_study", None)
            ) for plot in generator_instance.generate()
        ]
