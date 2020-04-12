"""
Base plot module.
"""

import typing as tp
import abc
from pathlib import Path

import matplotlib.pyplot as plt

from varats.plots.plots import PlotRegistry


class PlotDataEmpty(Exception):
    """
    Throw if there was no input data for plotting.
    """


class Plot(metaclass=PlotRegistry):
    """
    An abstract base class for all plots generated by VaRA-TS
    """

    def __init__(self, name: str, **kwargs: tp.Any) -> None:
        self.__name = name
        self.__style = "classic"
        self.__saved_extra_args = kwargs

    @property
    def name(self) -> str:
        """
        Name of the current plot.

        Test:
        >>> Plot('test').name
        'test'
        """
        return self.__name

    @property
    def style(self) -> str:
        """
        Current plot style

        Test:
        >>> Plot('test').style
        'classic'
        """
        return self.__style

    @style.setter
    def style(self, new_style: str) -> None:
        """
        Access current style of the plot.
        """
        self.__style = new_style

    @property
    def plot_kwargs(self) -> tp.Any:
        """
        Access the kwargs passed to the initial plot.

        Test:
        >>> p = Plot('test', foo='bar', baz='bazzer')
        >>> p.plot_kwargs['foo']
        'bar'
        >>> p.plot_kwargs['baz']
        'bazzer'
        """
        return self.__saved_extra_args

    @staticmethod
    def supports_stage_separation() -> bool:
        """
        True, if the plot supports stage separation, i.e., the plot can be draw
        separating the different stages in a case study.
        """
        return False

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file"""

    @abc.abstractmethod
    def show(self) -> None:
        """Show the current plot"""

    def save(self, path: tp.Optional[Path] = None,
             filetype: str = 'svg') -> None:
        """
        Save the current plot to a file.

        Args:
            path: The path where the file is stored (excluding the file name).
            filetype: The file type of the plot.
        """
        self.plot(False)

        if path is None:
            plot_dir = Path(self.plot_kwargs["plot_dir"])
        else:
            plot_dir = path
        project_name = self.plot_kwargs["project"]

        if self.plot_kwargs["ignore_whitespace"]:
            whitespace = "_ignore_whitespace"
        else:
            whitespace = ""

        plt.savefig(plot_dir /
                    (project_name + "_{graph_name}{whitespace}{stages}.{filetype}".format(
                        graph_name=self.name,
                        stages='S' if self.plot_kwargs['sep_stages'] else '',
                        filetype=filetype,
                        whitespace=whitespace)),
                    dpi=1200,
                    bbox_inches="tight",
                    format=filetype)

    @abc.abstractmethod
    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        """
        Calculate a list of revisions that could improve precisions of this
        plot.

        Args:
            boundary_gradient: The maximal expected gradient in percent between
                               two revisions, every thing that exceeds the
                               boundary should be further analyzed.
        """
