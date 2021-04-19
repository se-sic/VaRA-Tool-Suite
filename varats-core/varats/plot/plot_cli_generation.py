"""Module for generating the CLI for a plot."""
import typing as tp
from enum import Enum


class _CaseStudySelector(Enum):
    SPECIFIC = 0
    ALL = 1
    NONE = 2


class _RevisionSelector(Enum):
    SPECIFIC = 0
    NEWEST = 1
    ALL = 2
    NONE = 3


class _PlotCLIGenerationContext():

    def __init__(self):
        self.case_study_selector = _CaseStudySelector.NONE
        self.revision_selector = _RevisionSelector.ALL
        self.__custom_arguments: tp.List[tp.Tuple[str, str]] = []

    def add_custom_argument(self, arg_name: str, help_text: str):
        self.__custom_arguments.append((arg_name, help_text))


class PlotCLIBuilder():
    """Builder for creating command line interfaces for plot generators."""

    def __init__(self):
        self.__generation_context = _PlotCLIGenerationContext()

    def specific_case_study(self):
        """
        The user is required to provide the name of a case study.

        Plots will be generated using only this case study. The case study must
        be part of the current paper config.
        """
        self.__generation_context.specific_case_study = _CaseStudySelector.SPECIFIC
        return _CaseStudySelector(self.__generation_context)

    def all_case_studies(self):
        """Plots will be generated using all case studies of the current paper
        config."""
        self.__generation_context.specific_case_study = _CaseStudySelector.ALL
        return _CaseStudySelector(self.__generation_context)

    def specific_revision(self):
        """
        The user is required to provide a commit hash.

        Plots will be generated using only this commit. It suffices to specify a
        unique prefix of the commit hash, otherwise, an exception is thrown.
        #TODO: which one?
        """
        self.__generation_context.revision_selector = _RevisionSelector.SPECIFIC
        return _RevisionSelector(self.__generation_context)


class _PlotCLIBuilderCaseStudySelected():

    def __init__(self, generation_context: _PlotCLIGenerationContext):
        self.__generation_context = generation_context

    def newest_revision(self):
        """Plots will be generated using the newest available revision of each
        selected case study."""
        self.__generation_context.revision_selector = _RevisionSelector.NEWEST
        return _RevisionSelector(self.__generation_context)

    def all_revisions(self):
        """Plots will be generated using all revision of each selected case
        study."""
        self.__generation_context.revision_selector = _RevisionSelector.ALL
        return _RevisionSelector(self.__generation_context)

    def no_revision_selection(self):
        """Plot does not require revision selection."""
        self.__generation_context.revision_selector = _RevisionSelector.NONE
        return _RevisionSelector(self.__generation_context)


class _PlotCLIBuilderRevisionSelected():

    def __init__(self, generation_context: _PlotCLIGenerationContext):
        self.__generation_context = generation_context

    def add_custom_argument(
        self, arg_name: str, help_text: str
    ) -> '_PlotCLIBuilderRevisionSelected':
        """
        Add a custom argument to the CLI of this plot.

        Args:
            arg_name: name of the argument
            help_text: help text for this argument
        """
        self.__generation_context.add_custom_argument(arg_name, help_text)
        return self

    def create_cli(self):
        """
        Create the command line interface from this specification.

        TODO: arguments and return type depend on the used CLI library

        Returns:
        """
        pass
