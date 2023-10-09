from enum import Enum
from typing import MutableSequence
from varats.experiment.experiment_util import Step

from varats.project.varats_project import VProject

from varats.experiments.vara.instrumentation_verifier import RunInstrVerifier, RunInstrVerifierBudget


class OptimizerPolicyType(Enum):
    NONE = "none"
    NAIVE = "naive"
    ALTERNATING = "alternating"


class RunInstrVerifierNaive(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N"
):
    NAME = "RunInstrVerifierNaive"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-debug-only=OPT,IRT,InstrMark"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive40(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N40"
):
    NAME = "RunInstrVerifierNaive40"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=40", "-mllvm",
            "-debug-only=OPT,IRT,InstrMark"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive60(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N60"
):
    NAME = "RunInstrVerifierNaive60"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=60", "-mllvm",
            "-debug-only=OPT,IRT,InstrMark"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive80(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N60"
):
    NAME = "RunInstrVerifierNaive80"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=80", "-mllvm",
            "-debug-only=OPT,IRT,InstrMark"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierAlternating(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "A"
):
    NAME = "RunInstrVerifierAlternating"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=alternating", "-mllvm",
            "-debug-only=OPT,IRT,InstrMark"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaiveBudget(
    RunInstrVerifierBudget, shorthand=RunInstrVerifierBudget.SHORTHAND + "N"
):
    NAME = "RunInstrVerifierNaiveBudget"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-debug-only=OPT,IRT,InstrMark"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierAlternatingBudget(
    RunInstrVerifierBudget, shorthand=RunInstrVerifierBudget.SHORTHAND + "A"
):
    NAME = "RunInstrVerifierAlternatingBudget"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += ["-mllvm", "-vara-optimizer-policy=alternating"]
        return super().actions_for_project(project)
