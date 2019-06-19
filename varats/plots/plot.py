"""
Base plot module.
"""

import typing as tp
import abc


class Plot():
    """
    An abstract base class for all plots generated by VaRA-TS
    """

    def __init__(self, name):
        self.__name = name
        self.__style = "classic"

    @property
    def name(self) -> str:
        """
        Name of the current plot.
        """
        return self.__name

    @property
    def style(self) -> str:
        """
        Current plot style
        """
        return self.__style

    @style.setter
    def style(self, new_style):
        self.__style = new_style

    @staticmethod
    def supports_stage_separation() -> bool:
        """
        True, if the plot supports stage separation, i.e., the plot can be draw
        separating the different stages in a case study.
        """
        return False

    @abc.abstractmethod
    def plot(self):
        """Plot the current plot to a file"""

    @abc.abstractmethod
    def show(self):
        """Show the current plot"""

    @abc.abstractmethod
    def save(self, filetype='svg'):
        """Save the current plot to a file"""

    @abc.abstractmethod
    def calc_missing_revisions(self, boundary_gradient) -> tp.Set:
        """
        Calculate a list of revisions that could improve precisions of this
        plot.

        Args:
            boundary_gradient: The maximal expected gradient in percent between
                               two revisions, every thing that exceeds the
                               boundary should be further analyzed.
        """
