from enum import Enum
from typing import MutableSequence
from varats.experiment.experiment_util import Step

from varats.project.varats_project import VProject

from varats.experiments.vara.instrumentation_verifier import RunInstrVerifier, RunInstrVerifierBudget


class OptimizerPolicyType(Enum):
    NONE = "none"
    NAIVE = "naive"
    ALTERNATING = "alternating"


class RunInstrVerifierNaive20(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N20"
):
    NAME = "RunInstrVerifierNaive20"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=20"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive40(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N40"
):
    NAME = "RunInstrVerifierNaive40"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=40"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive60(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N60"
):
    NAME = "RunInstrVerifierNaive60"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=60"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive80(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N80"
):
    NAME = "RunInstrVerifierNaive80"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=80"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive100(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N100"
):
    NAME = "RunInstrVerifierNaive100"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=100"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive200(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N200"
):
    NAME = "RunInstrVerifierNaive200"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=200"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive500(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N500"
):
    NAME = "RunInstrVerifierNaive500"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=500"
        ]
        return super().actions_for_project(project)


class RunInstrVerifierNaive1000(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "N1000"
):
    NAME = "RunInstrVerifierNaive1000"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += [
            "-mllvm", "-vara-optimizer-policy=naive", "-mllvm",
            "-vara-optimizer-starting-budget=1000"
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
