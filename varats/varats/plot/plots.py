"""General plots module."""
import abc
import logging
import typing as tp
from pathlib import Path

import click

from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.paper_config import get_paper_config
from varats.ts_utils.cli_util import (
    make_cli_option,
    CLIOptionTy,
    add_cli_options,
    cli_yn_choice,
    TypedMultiChoice,
    TypedChoice,
)
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
    paper_config = get_paper_config()
    value_dict = {
        f"{cs.project_name}_{cs.version}": [cs]
        for cs in paper_config.get_all_case_studies()
    }
    value_dict["all"] = paper_config.get_all_case_studies()
    return TypedMultiChoice(value_dict)


def _create_single_case_study_choice() -> TypedChoice[CaseStudy]:
    """Create a choice parameter type that allows selecting exactly one case
    study from the current paper config."""
    paper_config = get_paper_config()
    value_dict = {
        f"{cs.project_name}_{cs.version}": cs
        for cs in paper_config.get_all_case_studies()
    }
    return TypedChoice(value_dict)


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
    def from_kwargs(**kwargs: tp.Any) -> 'CommonPlotOptions':
        """Construct a ``CommonPlotOptions`` object from a kwargs dict."""
        return CommonPlotOptions(
            kwargs.get("view", False),
            Path(kwargs.get("plot_dir", CommonPlotOptions.default_plot_dir())),
            kwargs.get("file_type", "svg")
        )

    @staticmethod
    def default_plot_dir() -> Path:
        return Path(str(vara_cfg()['plots']['plot_dir']))

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
            default="png",
            help="File type for the plot."
        ),
        make_cli_option(
            "--plot-dir",
            type=click.Path(
                exists=True,
                file_okay=False,
                dir_okay=True,
                writable=True,
                resolve_path=True,
                path_type=Path
            ),
            default=lambda: CommonPlotOptions.default_plot_dir(),
            help="Set the directory the plots will be written to."
            "Uses the config value 'plots/plot_dir' by default."
        )
    ]

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        return add_cli_options(command, *cls.__options)

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        return {
            "view": self.view,
            "file_type": self.file_type,
            "plot_dir": self.plot_dir
        }


class PlotConfig():
    """Class with parameters that influence a plot's appearance."""

    def __init__(self):
        pass

    __options: tp.List[tp.Any] = []

    @classmethod
    def cli_options(cls, command: tp.Any) -> tp.Any:
        return add_cli_options(command, *cls.__options)

    def get_dict(self) -> tp.Dict[str, tp.Any]:
        return {}


class PlotGeneratorInitFailed(Exception):
    """Base class for plot generator related exceptions."""

    def __init__(self, message: str):
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
    # TODO: Add report types as choices
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
        "-cs",
        "--case-study",
        type=_create_single_case_study_choice(),
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

    @staticmethod
    def get_plot_generator_types_help_string() -> str:
        """
        Generates help string for visualizing all available plots.

        Returns:
            a help string that contains all available plot names.
        """
        return "The following plot generators are available:\n  " + "\n  ".join(
            [key for key in PlotGenerator.GENERATORS]
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

    @abc.abstractmethod
    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        """This function is called to generate the plot instance(s)."""

    def __call__(self, common_options: CommonPlotOptions) -> None:
        """
        Generate the plots as specified by this generator.

        Args:
            common_options: common options to use for the plot(s)
        """
        if not common_options.plot_dir.exists():
            LOG.error(f"Could not find output dir {common_options.plot_dir}")

        plots = self.generate()

        if len(plots) > 1 and common_options.view:
            common_options.view = cli_yn_choice(
                f"Do you really want to view all {len(plots)} plots? "
                f"If you answer 'no', the plots will still be generated.", "n"
            )

        for plot in plots:
            if common_options.view:
                plot.show()
            else:
                plot.save(
                    common_options.plot_dir, filetype=common_options.file_type
                )
