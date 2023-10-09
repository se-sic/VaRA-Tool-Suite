"""Base class experiment and utilities for experiments that work with
features."""
import typing as tp
from abc import abstractmethod

from benchbuild.utils.actions import (
    Step,
)
from benchbuild.project import build_dir
import benchbuild.utils.actions as actns
from varats.experiment.experiment_util import Project
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.experiments.vara.feature_experiment import FeatureExperiment
from benchbuild.experiment import Actions


class Flags:

    def __init__(
        self,
        cflags: tp.Optional[tp.List[str]] = None,
        ldflags: tp.Optional[tp.List[str]] = None,
        result_folder_name: tp.Optional[str] = None
    ):
        self.__cflags = cflags or []
        self.__ldflags = ldflags or []
        self.__result_folder_name = result_folder_name

    @property
    def cflags(self) -> tp.List[str]:
        return self.__cflags

    @property
    def ldflags(self) -> tp.List[str]:
        return self.__ldflags

    @property
    def result_folder_name(self) -> tp.Optional[str]:
        return self.__result_folder_name

    def __str__(self):
        return f"Flags(cflags={self.cflags}, ldflags={self.ldflags}, result_folder_name={self.result_folder_name})"

    __repr__ = __str__


class MultiCompileExperiment(FeatureExperiment, shorthand=""):
    """Base class experiment for feature specific experiments."""

    NAME = "MultiCompileExperiment"

    REPORT_SPEC = ReportSpecification()

    @abstractmethod
    def actions_for_project(self, project: VProject,
                            flags: Flags) -> tp.MutableSequence[Step]:
        """Get the actions a project wants to run."""

    def get_flags(self) -> tp.List[Flags]:
        """Get a list of flags that should be changed for every compilation attempt"""
        return [Flags()]

    def actions(self) -> Actions:
        actions: Actions = []

        def new_actions(self, proj: Project, flags: Flags) -> Actions:
            atomic_actions: Actions = [
                tp.cast(Step, actns.Clean(proj)),
                actns.MakeBuildDir(proj),
                actns.Echo(
                    message=f"Selected {proj.name} with version {version_str}"
                ),
            ]
            if flags.cflags:
                atomic_actions.append(
                    actns.Echo(message=f"Set additional cflags {flags.cflags}")
                )
            if flags.ldflags:
                atomic_actions.append(
                    actns.Echo(
                        message=f"Set additional ldflags {flags.ldflags}"
                    )
                )
            if flags.result_folder_name:
                atomic_actions.append(
                    actns.Echo(
                        message=
                        f"Set result folder name override {flags.result_folder_name}"
                    )
                )
            atomic_actions.append(actns.ProjectEnvironment(proj))
            atomic_actions.extend(self.actions_for_project(proj))
            return [tp.cast(Step, actns.RequireAll(actions=atomic_actions))]

        for prj_cls in self.projects:
            prj_actions: Actions = []

            for revision in self.sample(prj_cls):
                version_str = str(revision)

                p = prj_cls(revision)

                for flags in self.get_flags():
                    p_clone = p.clone()

                    p_clone.cflags = flags.cflags
                    p_clone.ldflags = flags.ldflags
                    result_folder = flags.result_folder_name or str(p.run_uuid)
                    p_clone.builddir = build_dir(self, p_clone) / result_folder

                    prj_actions = new_actions(self, p_clone, flags)
                    actions.extend(prj_actions)

        if actions:
            actions.append(actns.CleanExtra())

        return actions


STARTING_BUDGET = 0
END_BUDGET = 100
BUDGET_STEP = 20


class VaryingStartingBudgetExperiment(MultiCompileExperiment, shorthand=""):
    NAME = "VaryingStartingBudgetExperiment"

    REPORT_SPEC = ReportSpecification()

    @abstractmethod
    def actions_for_project(self, project: VProject,
                            flags: Flags) -> tp.MutableSequence[Step]:
        """Get the actions a project wants to run."""

    def get_flags(self) -> tp.List[Flags]:
        flags = []
        for budget in range(STARTING_BUDGET, END_BUDGET, BUDGET_STEP):
            f = Flags(
                cflags=["-mllvm", f"-vara-optimizer-starting-budget={budget}"],
                result_folder_name=f"starting_budget_{budget}"
            )
            flags.append(f)
        return flags
