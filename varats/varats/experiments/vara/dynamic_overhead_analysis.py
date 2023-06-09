from enum import Enum
from typing import MutableSequence
from varats.experiment.experiment_util import Step
from varats.experiments.vara.feature_experiment import Flags

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
        project.cflags += ["-mllvm", f"-vara-optimizer-policy=naive"]
        return super().actions_for_project(project)


class RunInstrVerifierAlternating(
    RunInstrVerifier, shorthand=RunInstrVerifier.SHORTHAND + "A"
):
    NAME = "RunInstrVerifierAlternating"

    def actions_for_project(self, project: VProject) -> MutableSequence[Step]:
        project.cflags += ["-mllvm", f"-vara-optimizer-policy=alternating"]
        return super().actions_for_project(project)


class RunInstrVerifierNaiveBudget(
    RunInstrVerifierBudget, shorthand=RunInstrVerifier.SHORTHAND + "NB"
):
    NAME = "RunInstrVerifierNaiveBudget"

    def actions_for_project(self, project: VProject,
                            flags: Flags) -> MutableSequence[Step]:
        project.cflags += ["-mllvm", f"-vara-optimizer-policy=naive"]
        return super().actions_for_project(project, flags)


class RunInstrVerifierAlternatingBudget(
    RunInstrVerifierBudget, shorthand=RunInstrVerifier.SHORTHAND + "AB"
):
    NAME = "RunInstrVerifierAlternatingBudget"

    def actions_for_project(self, project: VProject,
                            flags: Flags) -> MutableSequence[Step]:
        project.cflags += ["-mllvm", f"-vara-optimizer-policy=alternating"]
        return super().actions_for_project(project, flags)
