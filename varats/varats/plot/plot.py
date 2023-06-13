"""Base plot module."""

import abc
import logging
import typing as tp
from functools import reduce
from pathlib import Path

import matplotlib.pyplot as plt

import varats.paper.case_study
from varats.plot.plots import PlotConfig
from varats.utils.git_util import FullCommitHash

if tp.TYPE_CHECKING:
    from varats.paper.case_study import CaseStudy  # pylint: disable=W0611

LOG = logging.getLogger(__name__)


class PlotDataEmpty(Exception):
    """Throw if there was no input data for plotting."""


class Plot:
    """An abstract base class for all plots generated by VaRA-TS."""

    NAME = "Plot"
    PLOTS: tp.Dict[str, tp.Type['Plot']] = {}

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any) -> None:
        self.__plot_config = plot_config
        self.__saved_extra_args = kwargs

    @classmethod
    def __init_subclass__(
        cls, *, plot_name: tp.Optional[str], **kwargs: tp.Any
    ) -> None:
        """
        Register concrete plots.

        Args:
            plot_name: name for the plot; if ``None``, do not register the plot
        """
        super().__init_subclass__(**kwargs)

        if plot_name:
            cls.NAME = plot_name
            cls.PLOTS[plot_name] = cls

    @staticmethod
    def get_plot_types_help_string() -> str:
        """
        Generates help string for visualizing all available plots.

        Returns:
            a help string that contains all available plot names.
        """
        return "The following plots are available:\n  " + "\n  ".join(
            list(Plot.PLOTS)
        )

    @staticmethod
    def get_class_for_plot_type(plot_type: str) -> tp.Type['Plot']:
        """
        Get the class for plot from the plot registry.

        Args:
            plot_type: The name of the plot.

        Returns: The class implementing the plot.
        """
        if plot_type not in Plot.PLOTS:
            raise LookupError(
                f"Unknown plot '{plot_type}'.\n" +
                Plot.get_plot_types_help_string()
            )

        plot_cls = Plot.PLOTS[plot_type]
        return plot_cls

    @property
    def name(self) -> str:
        """
        Name of the current plot.

        Test:
        >>> Plot(PlotConfig.from_kwargs(view=False)).name
        'Plot'
        """
        return self.NAME

    @property
    def plot_config(self) -> PlotConfig:
        """Plot config for this plot."""
        return self.__plot_config

    @property
    def plot_kwargs(self) -> tp.Any:
        """
        Access the kwargs passed to the initial plot.

        Test:
        >>> p = Plot(PlotConfig.from_kwargs(view=False),foo='bar',baz='bazzer')
        >>> p.plot_kwargs['foo']
        'bar'
        >>> p.plot_kwargs['baz']
        'bazzer'
        """
        return self.__saved_extra_args

    @staticmethod
    def supports_stage_separation() -> bool:
        """True, if the plot supports stage separation, i.e., the plot can be
        drawn separating the different stages in a case study."""
        return False

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

    def show(self) -> None:
        """Show the current plot."""
        try:
            self.plot(True)
        except PlotDataEmpty:
            LOG.warning("No data for the current project.")
            return
        plt.show()
        plt.close()

    def plot_file_name(self, filetype: str) -> str:
        """
        Get the file name this plot; will be stored to when calling save.

        Args:
            filetype: the file type for the plot

        Returns:
            the file name the plot will be stored to

        Test:
        >>> p = Plot(PlotConfig.from_kwargs(view=False),project='bar')
        >>> p.plot_file_name('svg')
        'bar_Plot.svg'
        >>> from varats.paper.case_study import CaseStudy
        >>> p = Plot(PlotConfig.from_kwargs(view=False),\
                     project='bar', case_study=CaseStudy('baz', 42))
        >>> p.plot_file_name('png')
        'baz_42_Plot.png'
        """
        plot_ident = ''
        if 'case_study' in self.plot_kwargs:
            case_study = self.plot_kwargs['case_study']
            if isinstance(case_study, varats.paper.case_study.CaseStudy):
                plot_ident = f"{case_study.project_name}_{case_study.version}_"
            else:
                plot_ident = \
                    f"{reduce(lambda x,y: f'{x}{y.project_name}_',case_study,'')}"
        elif 'project' in self.plot_kwargs:
            plot_ident = f"{self.plot_kwargs['project']}_"

        sep_stages = ''
        if self.supports_stage_separation(
        ) and self.plot_kwargs.get('sep_stages', None):
            sep_stages = 'S'

        return f"{plot_ident}{self.name}{sep_stages}.{filetype}"

    def save(self, plot_dir: Path, filetype: str = 'svg') -> None:
        """
        Save the current plot to a file.

        Args:
            plot_dir: the path where the file is stored (excluding file name)
            filetype: the file type of the plot
        """
        try:
            self.plot(False)
        except PlotDataEmpty:
            LOG.warning("No data for this plot.")
            return

        plt.savefig(
            plot_dir / self.plot_file_name(filetype),
            dpi=self.plot_config.dpi(),
            bbox_inches="tight",
            format=filetype
        )
        plt.close()

    @abc.abstractmethod
    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        """
        Calculate a list of revisions that could improve precisions of this
        plot.

        Raises an :class:`~varats.utils.exceptions.UnsupportedOperation` if not
        supported by a plot.

        Args:
            boundary_gradient: The maximal expected gradient in percent between
                               two revisions, every thing that exceeds the
                               boundary should be further analyzed.
        """
