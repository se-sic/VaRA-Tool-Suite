"""General plots module."""
import abc
import logging
import re
import typing as tp
from pathlib import Path

import click

from varats.plot.plot_utils import check_required_args
from varats.utils.cli_util import make_cli_option, CLIOptionTy, add_cli_options
from varats.utils.settings import vara_cfg

if tp.TYPE_CHECKING:
    import varats.plot.plot  # pylint: disable=W0611

LOG = logging.getLogger(__name__)


class PlotRegistry(abc.ABCMeta):
    """Registry for all supported plots."""

    to_snake_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')

    plots: tp.Dict[str, tp.Type[tp.Any]] = {}
    plots_discovered = False

    def __init__(
        cls, name: str, bases: tp.Tuple[tp.Any], attrs: tp.Dict[tp.Any, tp.Any]
    ):
        super(PlotRegistry, cls).__init__(name, bases, attrs)
        if hasattr(cls, 'NAME'):
            key = getattr(cls, 'NAME')
        else:
            key = PlotRegistry.to_snake_case_pattern.sub('_', name).lower()
        PlotRegistry.plots[key] = cls

    @staticmethod
    def get_plot_types_help_string() -> str:
        """
        Generates help string for visualizing all available plots.

        Returns:
            a help string that contains all available plot names.
        """
        return "The following plots are available:\n  " + "\n  ".join([
            key for key in PlotRegistry.plots if key != "plot"
        ])

    @staticmethod
    def get_class_for_plot_type(
        plot_type: str
    ) -> tp.Type['varats.plot.plot.Plot']:
        """
        Get the class for plot from the plot registry.

        Args:
            plot_type: The name of the plot.

        Returns: The class implementing the plot.
        """
        from varats.plot.plot import Plot  # pylint: disable=W0611
        if plot_type not in PlotRegistry.plots:
            raise LookupError(
                f"Unknown plot '{plot_type}'.\n" +
                PlotRegistry.get_plot_types_help_string()
            )

        plot_cls = PlotRegistry.plots[plot_type]
        if not issubclass(plot_cls, Plot):
            raise AssertionError()
        return plot_cls


class CommonPlotOptions():
    """This class stores options common to all plots."""

    def __init__(self, view: bool, plot_dir: Path, file_type: str):
        """
        Construct a `CommonPlotOptions` object.

        Args:
            view: if `True`, view the plot instead of writing it to a file
            plot_dir: the directory to write plots to
            file_type: the file type for the written plot file
        """
        self.view = view
        self.plot_dir = plot_dir
        self.file_type = file_type

    @staticmethod
    @check_required_args("view", "plot_dir", "file_type")
    def from_kwargs(**kwargs: tp.Any) -> 'CommonPlotOptions':
        """Construct a ``CommonPlotOptions`` object from a kwargs dict."""
        return CommonPlotOptions(
            kwargs['view'], Path(kwargs["plot_dir"]), kwargs["file_type"]
        )

    @classmethod
    def default_plot_dir(cls) -> Path:
        return Path(str(vara_cfg()['plots']['plot_dir']))

    __options = [
        make_cli_option(
            "-v",
            "--view",
            type=bool,
            default=False,
            help="View the plot instead of saving it to a file."
        ),
        make_cli_option(
            "--file-type",
            type=str,
            default="svg",  # todo: provide choices
            help="File type for the plot."
        ),
        make_cli_option(
            "--output-dir",
            type=click.Path(
                exists=True,
                file_okay=False,
                dir_okay=True,
                writable=True,
                resolve_path=True
            ),
            default=lambda: str(CommonPlotOptions.default_plot_dir()),
            help="Set the directory the plots will be written to."
            "Uses the config value 'plots/plot_dir' by default."
        )
    ]

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        return add_cli_options(command, *cls.__options)


class PlotConfig():
    """Class with parameters that influence a plot's appearance."""

    def __init__(self):
        pass

    __options = []

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        return add_cli_options(command, *cls.__options)


class PlotGenerator(abc.ABC):
    """A plot generator is responsible for generating one or more plots."""

    # Required
    REQUIRE_CASE_STUDY: CLIOptionTy = make_cli_option(
        "-cs"
        "--case-study",
        required=True,
        metavar="case_study",
        help="The case study to use for the plot."
    )
    REQUIRE_REVISION: CLIOptionTy = make_cli_option(
        "-rev",
        "--revision",
        required=True,
        metavar="revision",
        help="The revision to use for the plot."
    )
    REQUIRE_REPORT_TYPE: CLIOptionTy = make_cli_option(
        "--report-type",
        required=True,
        metavar="report_type",
        help="The report type to use for the plot."
    )

    # Optional
    OPTIONAL_REVISION: CLIOptionTy = make_cli_option(
        "-rev",
        "--revision",
        required=False,
        metavar="revision",
        help="The revision to use for the plot."
    )

    OPTIONAL_CASE_STUDY: CLIOptionTy = make_cli_option(
        "-cs"
        "--case-study",
        required=False,
        metavar="case_study",
        help="The case study to use for the plot."
    )

    GENERATORS: tp.Dict[str, tp.Type['PlotGenerator']] = {}
    NAME: str
    PLOT: tp.Type['varats.plot.plot.Plot']
    OPTIONS: tp.List[CLIOptionTy]

    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        self.__plot_config = plot_config
        self.__plot_kwargs = plot_kwargs

    @classmethod
    def __init_subclass__(
        cls, generator_name: str, plot: tp.Type['varats.plot.plot.Plot'],
        options: tp.List[CLIOptionTy], **kwargs: tp.Any
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
        cls.PLOT = plot
        cls.OPTIONS = options
        cls.GENERATORS[generator_name] = cls

    @property
    def plot_config(self) -> PlotConfig:
        """Option with options that influence a plot's appearance."""
        return self.__plot_config

    @abc.abstractmethod
    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        """This function is called to generate the plot instance(s)."""

    def __call__(self, common_options: CommonPlotOptions):
        """
        Generate the plots as specified by this generator.

        Args:
            common_options: common options to use for the plot(s)
        """
        if not common_options.plot_dir.exists():
            LOG.error(f"Could not find output dir {common_options.plot_dir}")
            return []

        plots = self.generate()
        for plot in plots:
            if common_options.view:
                plot.show()
            else:
                plot.save(
                    common_options.plot_dir, filetype=common_options.file_type
                )
