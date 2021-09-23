"""General plots module."""
import abc
import logging
import typing as tp
from pathlib import Path

import click

from varats.data.discover_reports import initialize_reports
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.artefacts import Artefact, ArtefactFileInfo
from varats.paper_mgmt.paper_config import get_paper_config
from varats.report.report import BaseReport
from varats.ts_utils.cli_util import (
    make_cli_option,
    CLIOptionTy,
    add_cli_options,
    cli_yn_choice,
    TypedMultiChoice,
    TypedChoice,
)
from varats.utils.exceptions import ConfigurationLookupError
from varats.utils.settings import vara_cfg

if tp.TYPE_CHECKING:
    import varats.plot.plot  # pylint: disable=W0611

LOG = logging.getLogger(__name__)


def _create_multi_case_study_choice() -> TypedMultiChoice[CaseStudy]:
    """
    Create a choice parameter type that allows selecting multiple case studies
    from the current paper config.

    Multiple case studies can be given as a comma separated list. The special
    value "all" selects all case studies in the current paper config.
    """
    try:
        paper_config = get_paper_config()
    except ConfigurationLookupError:
        empty_cs_dict: tp.Dict[str, tp.List[CaseStudy]] = {}
        return TypedMultiChoice(empty_cs_dict)
    value_dict = {
        f"{cs.project_name}_{cs.version}": [cs]
        for cs in paper_config.get_all_case_studies()
    }
    value_dict["all"] = paper_config.get_all_case_studies()
    return TypedMultiChoice(value_dict)


def _create_single_case_study_choice() -> TypedChoice[CaseStudy]:
    """Create a choice parameter type that allows selecting exactly one case
    study from the current paper config."""
    try:
        paper_config = get_paper_config()
    except ConfigurationLookupError:
        empty_cs_dict: tp.Dict[str, CaseStudy] = {}
        return TypedChoice(empty_cs_dict)
    value_dict = {
        f"{cs.project_name}_{cs.version}": cs
        for cs in paper_config.get_all_case_studies()
    }
    return TypedChoice(value_dict)


def _create_report_type_choice() -> TypedChoice[tp.Type[BaseReport]]:
    """Create a choice parameter type that allows selecting a report type."""
    initialize_reports()
    return TypedChoice(BaseReport.REPORT_TYPES)


class CommonPlotOptions():
    """This class stores options common to all plots."""

    def __init__(
        self, view: bool, plot_dir: Path, file_type: str, dry_run: bool
    ):
        """
        Construct a `CommonPlotOptions` object.

        Args:
            view: if `True`, view the plot instead of writing it to a file
            plot_dir: directory to write plots to
                      (relative to config value 'plots/plot_dir')
            file_type: the file type for the written plot file
        """
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
        return add_cli_options(command, *cls.__options)

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        return {
            "view": self.view,
            "file_type": self.file_type,
            "plot_dir": self.plot_dir,
            "dry_run": self.dry_run
        }


class PlotConfig:
    """Class with parameters that influence a plot's appearance."""

    def __init__(
        self, style: str, fig_title: str, font_size: int, width: int,
        height: int, legend_title: str, legend_size: int, show_legend: bool,
        line_width: bool, x_tick_size: int, label_size: int, dpi: int
    ) -> None:
        self.style = style
        self.fig_title = fig_title
        self.font_size = font_size
        self.width = width
        self.height = height
        self.legend_title = legend_title
        self.legend_size = legend_size
        self.show_legend = show_legend
        self.line_width = line_width
        self.x_tick_size = x_tick_size
        self.label_size = label_size
        self.dpi = dpi

    __options: tp.List[tp.Any] = [
        make_cli_option(
            "--style",
            type=str,
            default="classic",
            required=False,
            metavar="STYLE",
            help="Matplotlib style to use."
        ),
        make_cli_option(
            "--fig-title",
            type=str,
            default="",
            required=False,
            metavar="NAME",
            help="The title of the plot figure."
        ),
        make_cli_option(
            "--font-size",
            type=int,
            default=10,
            required=False,
            metavar="SIZE",
            help="The font size of the plot figure."
        ),
        make_cli_option(
            "--width",
            type=int,
            default=1500,
            required=False,
            metavar="WIDTH",
            help="The width of the resulting plot file."
        ),
        make_cli_option(
            "--height",
            type=int,
            default=1000,
            required=False,
            metavar="HEIGHT",
            help="The height of the resulting plot file."
        ),
        make_cli_option(
            "--legend-title",
            type=str,
            default="",
            required=False,
            metavar="NAME",
            help="The title of the legend."
        ),
        make_cli_option(
            "--legend-size",
            type=int,
            default=2,
            required=False,
            metavar="SIZE",
            help="The size of the legend."
        ),
        make_cli_option(
            "--show-legend/--hide-legend",
            type=bool,
            default=True,
            required=False,
            help="Shows/hides the legend."
        ),
        make_cli_option(
            "--line-width",
            type=float,
            default=0.25,
            required=False,
            metavar="WIDTH",
            help="The width of the plot line(s)."
        ),
        make_cli_option(
            "--x-tick-size",
            type=int,
            default=2,
            required=False,
            metavar="SIZE",
            help="The size of the x-ticks."
        ),
        make_cli_option(
            "--label-size",
            type=int,
            default=2,
            required=False,
            metavar="SIZE",
            help="The label size of CVE/bug annotations."
        ),
        make_cli_option(
            "--dpi",
            type=int,
            default=1200,
            required=False,
            metavar="DPI",
            help="The dpi of the plot."
        )
    ]

    @staticmethod
    def from_kwargs(**kwargs: tp.Any) -> 'PlotConfig':
        return PlotConfig(
            kwargs.get("style", "classic"), kwargs.get("fig_title", ""),
            kwargs.get("font_size", 10), kwargs.get("width", 1500),
            kwargs.get("height", 1000), kwargs.get("legend_title", ""),
            kwargs.get("legend_size", 2), kwargs.get("show_legend", True),
            kwargs.get("line_width", 0.25), kwargs.get("x_tick_size", 2),
            kwargs.get("label_size", 2), kwargs.get("dpi", 1200)
        )

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        return add_cli_options(command, *cls.__options)

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        return {
            "style": self.style,
            "fig_title": self.fig_title,
            "font_size": self.font_size,
            "width": self.width,
            "height": self.height,
            "legend_title": self.legend_title,
            "legend_size": self.legend_size,
            "show_legend": self.show_legend,
            "line_width": self.line_width,
            "x_tick_size": self.x_tick_size,
            "label_size": self.label_size,
            "dpi": self.dpi
        }


class PlotGeneratorInitFailed(Exception):
    """Base class for plot generator related exceptions."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class PlotGenerator(abc.ABC):
    """A plot generator is responsible for generating one or more plots."""

    # Required
    REQUIRE_CASE_STUDY: CLIOptionTy = make_cli_option(
        "-cs",
        "--case-study",
        type=_create_single_case_study_choice(),
        required=True,
        metavar="case_study",
        help="The case study to use for the plot."
    )
    REQUIRE_MULTI_CASE_STUDY: CLIOptionTy = make_cli_option(
        "-cs",
        "--case-study",
        type=_create_multi_case_study_choice(),
        required=True,
        metavar="case_study",
        help="The case study to use for the plot."
    )
    REQUIRE_REVISION: CLIOptionTy = make_cli_option(
        "-rev",
        "--revision",
        type=str,
        required=True,
        metavar="revision",
        help="The revision to use for the plot."
    )
    REQUIRE_REPORT_TYPE: CLIOptionTy = make_cli_option(
        "--report-type",
        type=_create_report_type_choice(),
        required=True,
        help="The report type to use for the plot."
    )

    GENERATORS: tp.Dict[str, tp.Type['PlotGenerator']] = {}
    NAME: str
    OPTIONS: tp.List[CLIOptionTy]

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
            generator_name: name for the plot generator as will be used in the
                            CLI interface
            plot:           plot class used by the generator
            options:        command line options needed by the generator
        """
        # mypy does not yet fully understand __init_subclass__()
        # https://github.com/python/mypy/issues/4660
        super().__init_subclass__(**kwargs)  # type: ignore
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
        plot_type: str
    ) -> tp.Type['PlotGenerator']:
        """
        Get the class for plot from the plot registry.

        Args:
            plot_type: The name of the plot.

        Returns: The class implementing the plot.
        """
        if plot_type not in PlotGenerator.GENERATORS:
            raise LookupError(
                f"Unknown plot generator '{plot_type}'.\n" +
                PlotGenerator.get_plot_generator_types_help_string()
            )

        plot_cls = PlotGenerator.GENERATORS[plot_type]
        return plot_cls

    @property
    def plot_config(self) -> PlotConfig:
        """Option with options that influence a plot's appearance."""
        return self.__plot_config

    @property
    def plot_kwargs(self) -> tp.Dict[str, tp.Any]:
        """Plot-specific options."""
        return self.__plot_kwargs

    @abc.abstractmethod
    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        """This function is called to generate the plot instance(s)."""

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


class PlotArtefact(Artefact, artefact_type="plot", artefact_type_version=2):
    """
    An artefact defining a :class:`plot<varats.plot.plot.Plot>`.

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
        """A config object that influences the visual representation of a
        plot."""
        return self.__plot_config

    @property
    def plot_kwargs(self) -> tp.Any:
        """Additional arguments that will be passed to the plot_type_class."""
        return self.__plot_kwargs

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        artefact_dict = super().get_dict()
        artefact_dict['plot_generator'] = self.__plot_generator_type
        artefact_dict['plot_config'] = self.__plot_config.get_dict()
        artefact_dict = {
            **self.__common_options.get_dict(),
            **self.__plot_kwargs,
            **artefact_dict
        }
        artefact_dict.pop("plot_dir")  # duplicate of Artefact's output_path
        return artefact_dict

    @staticmethod
    def create_artefact(
        name: str, output_dir: Path, **kwargs: tp.Any
    ) -> 'Artefact':
        plot_generator_type = kwargs.pop('plot_generator')
        common_options = CommonPlotOptions.from_kwargs(**kwargs)
        plot_config = PlotConfig.from_kwargs(**kwargs.pop("plot_config", {}))
        return PlotArtefact(
            name, output_dir, plot_generator_type, common_options, plot_config,
            **kwargs
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
        """Returns a list of file meta-date generated by this artefact."""
        generator_instance = self.plot_generator_class(
            self.plot_config, **self.__plot_kwargs
        )
        return [
            ArtefactFileInfo(
                plot.plot_file_name(self.common_options.file_type),
                plot.plot_kwargs.get("case_study", None)
            ) for plot in generator_instance.generate()
        ]
