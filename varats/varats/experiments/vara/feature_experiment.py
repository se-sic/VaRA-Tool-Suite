"""Base class experiment and utilities for experiments that work with
features."""
# TODO: figure out where to put the file
import typing as tp
from abc import abstractmethod
from pathlib import Path

from benchbuild.project import Project
from benchbuild.utils.actions import Step

from varats.experiment.experiment_util import VersionExperiment
from varats.project.varats_project import VProject
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)


class FeatureExperiment(VersionExperiment, shorthand=""):

    @abstractmethod
    def actions_for_project(self, project: Project) -> tp.MutableSequence[Step]:
        """Get the actions a project wants to run."""

    @staticmethod
    def get_feature_model_path(project: VProject) -> Path:
        """Get access to the feature model for a given project."""
        fm_provider = FeatureModelProvider.create_provider_for_project(
            type(project)
        )
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        return fm_path

    @staticmethod
    def get_vara_feature_cflags(project: VProject) -> tp.List[str]:
        fm_path = FeatureExperiment.get_feature_model_path(project).absolute()
        return ["-fvara-feature", f"-fvara-fm-path={fm_path}"]

    @staticmethod
    def get_vara_tracing_cflags(instr_type: str,
                                save_temps: bool = False) -> tp.List[str]:
        c_flags = [
            "-fsanitize=vara", f"-fvara-instr={instr_type}", "-flto",
            "-fuse-ld=lld", "-flegacy-pass-manager"
        ]
        if save_temps:
            c_flags += ["-Wl,-plugin-opt=save-temps"]

        return c_flags

    @staticmethod
    def get_vara_tracing_ldflags() -> tp.List[str]:
        return ["-flto"]
