"""Custom version of benchbuild's Command for use with the VaRA-Tool-Suite."""
import typing as tp

from benchbuild.command import Command, ProjectCommand

from varats.experiment.experiment_util import get_config_patches
from varats.project.varats_project import VProject


class VCommand(Command):  # type: ignore [misc]
    """
    Wrapper around benchbuild's Command class.

    Attributes:
    requires_any_args: any of these command line args must be available for
                       successful execution.
    requires_all_args: all of these command line args must be available for
                       successful execution.
    requires_any_patch: any of these patch feature-tags must be available for
                       successful execution.
    requires_all_patch: all of these patch feature-tags must be available for
                       successful execution.
    """

    _requires: tp.Set[str]

    def __init__(
        self,
        *args: tp.Any,
        requires_any_args: tp.Optional[tp.Set[str]] = None,
        requires_all_args: tp.Optional[tp.Set[str]] = None,
        requires_any_patch: tp.Optional[tp.Set[str]] = None,
        requires_all_patch: tp.Optional[tp.Set[str]] = None,
        **kwargs: tp.Union[str, tp.List[str]],
    ) -> None:

        super().__init__(*args, **kwargs)
        self._requires_any_args = requires_any_args or set()
        self._requires_all_args = requires_all_args or set()
        self._requires_any_patch = requires_any_patch or set()
        self._requires_all_patch = requires_all_patch or set()

    @property
    def requires_any_args(self) -> tp.Set[str]:
        return self._requires_any_args

    @property
    def requires_all_args(self) -> tp.Set[str]:
        return self._requires_all_args

    @property
    def requires_any_patch(self) -> tp.Set[str]:
        return self._requires_any_patch

    @property
    def requires_all_patch(self) -> tp.Set[str]:
        return self._requires_all_patch


class VProjectCommand(ProjectCommand):  # type: ignore

    def __init__(self, project: VProject, command: Command):
        super().__init__(project, command)
        self.v_command = command if isinstance(command, VCommand) else None
        self.v_project = project

    def can_be_executed(self) -> bool:
        """
        Checks whether this command can be executed with the given
        configuration.

        Returns:
            whether this command can be executed
        """
        # non-VCommands do not support filtering by configuration, so we default
        # to using them as-is
        if self.v_command is None:
            return True

        all_args = self.v_command.as_plumbum(project=self.project).args
        all_patch_tags: tp.Set[str] = set()

        for patch in get_config_patches(self.v_project):
            if patch.feature_tags:
                all_patch_tags.update(patch.feature_tags)

        return bool((
            not self.v_command.requires_any_args or
            all_args.intersection(self.v_command.requires_any_args)
        ) and (
            not self.v_command.requires_all_args or
            self.v_command.requires_all_args.issubset(all_args)
        ) and (
            not self.v_command.requires_any_patch or
            all_patch_tags.intersection(self.v_command.requires_any_patch)
        ) and (
            not self.v_command.requires_all_patch or
            self.v_command.requires_all_patch.issubset(all_patch_tags)
        ))
