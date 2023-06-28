import typing as tp

from benchbuild import Project
from benchbuild.utils import actions

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import VersionExperiment
from varats.experiments.base.just_compile import JustCompileReport
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.report import ReportSpecification
from varats.utils.git_util import ShortCommitHash

# Placeholder until we figure out how to pass experiment parameters to this
EXPERIMENTS = [JustCompileReport]


class ApplyPatch(actions.ProjectStep):
    pass


class RevertPatch(actions.ProjectStep):
    pass


class PatchExperiment(VersionExperiment, shorthand="PE"):
    """Generates empty report file."""

    NAME = "PatchExperiment"
    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(
            self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the aggregated steps for all experiments and the various patches."""
        analysis_actions = []

        for experiment in EXPERIMENTS:
            # In any case we always want to run the experiment without any patches
            analysis_actions.append(actions.RequireAll(experiment.actions_for_project(project)))

            patch_provider = PatchProvider.get_provider_for_project(project.cls)

            # This seems brittle but I don't know how to get the current revision
            commit_hash = ShortCommitHash(str(project.revision))

            patches = patch_provider.patches_config.get_patches_for_revision(commit_hash)

            for patch in patches:
                patch_actions = [ApplyPatch(project, patch),
                                 experiment.actions_for_project(project) ,
                                 RevertPatch(project, patch)]

                analysis_actions.append(actions.RequireAll(patch_actions))

        return analysis_actions
