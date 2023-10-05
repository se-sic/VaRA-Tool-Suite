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
            "-mllvm", "-vara-optimizer-policy=naive", "-vara-optimizer-starting-budget=0", "-mllvm",
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

class RunInstrVerifierLoopExtract(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "L"
):
    NAME = "RunInstrVerifierLoopExtract"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=loop_extract", "-mllvm",
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

