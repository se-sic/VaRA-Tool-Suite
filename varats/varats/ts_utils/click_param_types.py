"""Module for custom click parameter types."""

import typing as tp
from enum import Enum

import benchbuild as bb
import click

from varats.data.discover_reports import initialize_reports
from varats.experiment.experiment_util import VersionExperiment
from varats.experiments.discover_experiments import initialize_experiments
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.paper_config import get_paper_config
from varats.report.report import BaseReport
from varats.utils.exceptions import ConfigurationLookupError

ChoiceTy = tp.TypeVar("ChoiceTy")


class TypedChoice(click.Choice, tp.Generic[ChoiceTy]):
    """Typed version of click's choice parameter type."""

    name = "typed choice"

    def __init__(
        self, choices: tp.Dict[str, ChoiceTy], case_sensitive: bool = True
    ):
        self.__choices = choices
        super().__init__(list(choices.keys()), case_sensitive)

    def convert(
        self, value: tp.Any, param: tp.Optional[click.Parameter],
        ctx: tp.Optional[click.Context]
    ) -> ChoiceTy:
        return self.__choices[
            #  pylint: disable=super-with-arguments
            super(TypedChoice, self).convert(value, param, ctx)]


class TypedMultiChoice(click.Choice, tp.Generic[ChoiceTy]):
    """
    Typed choice parameter type allows giving multiple values.

    Multiple values can be given as a comma separated list; no whitespace
    allowed.
    """

    name = "typed multi choice"

    def __init__(
        self,
        choices: tp.Dict[str, tp.List[ChoiceTy]],
        case_sensitive: bool = True
    ):
        self.__choices = choices
        super().__init__(list(choices.keys()), case_sensitive)

    def convert(
        self, value: tp.Any, param: tp.Optional[click.Parameter],
        ctx: tp.Optional[click.Context]
    ) -> tp.List[ChoiceTy]:
        values = [value]
        if isinstance(value, str):
            values = list(map(str.strip, value.split(",")))

        return [
            item for v in values for item in self.__choices[
                #  pylint: disable=super-with-arguments
                super(TypedMultiChoice, self).convert(v, param, ctx)]
        ]


EnumTy = tp.TypeVar("EnumTy", bound=Enum)


class EnumChoice(click.Choice, tp.Generic[EnumTy]):
    """
    Enum choice type for click.

    This type can be used with click to specify a choice from the given enum.
    """

    def __init__(self, enum: tp.Type[EnumTy], case_sensitive: bool = True):
        self.__enum = enum
        super().__init__(list(dict(enum.__members__).keys()), case_sensitive)

    def convert(
        self, value: tp.Union[str, EnumTy], param: tp.Optional[click.Parameter],
        ctx: tp.Optional[click.Context]
    ) -> EnumTy:
        if isinstance(value, str):
            return self.__enum[super().convert(value, param, ctx)]
        return value


def create_multi_case_study_choice() -> TypedMultiChoice[CaseStudy]:
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


def create_single_case_study_choice() -> TypedChoice[CaseStudy]:
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


def create_report_type_choice() -> TypedChoice[tp.Type[BaseReport]]:
    """Create a choice parameter type that allows selecting a report type."""
    initialize_reports()
    return TypedChoice(BaseReport.REPORT_TYPES)


def create_experiment_type_choice() -> TypedChoice[tp.Type[VersionExperiment]]:
    """Create a choice parameter type that allows selecting a report type."""

    def is_experiment_excluded(experiment_name: str) -> bool:
        """Checks if an experiment should be excluded, as we don't want to
        show/use standard BB experiments."""
        if experiment_name in ('raw', 'empty', 'no-measurement'):
            return True

        return False

    initialize_experiments()
    return TypedChoice({
        k: v
        for k, v in bb.experiment.ExperimentRegistry.experiments.items()
        if not is_experiment_excluded(k)
    })
