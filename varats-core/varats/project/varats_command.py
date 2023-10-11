"""Custom version of benchbuild's Command for use with the VaRA-Tool-Suite."""
import typing as tp
from pathlib import Path

from benchbuild.command import Command, ProjectCommand, PathToken
from benchbuild.utils.cmd import time
from plumbum import local
from plumbum.commands.base import BaseCommand
from plumbum.machines import LocalCommand

from varats.utils.config import get_config_patches

if tp.TYPE_CHECKING:
    from plumbum.commands.base import BoundEnvCommand

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
        redirect_stdin: tp.Optional[PathToken] = None,
        redirect_stdout: tp.Optional[PathToken] = None,
        **kwargs: tp.Union[str, tp.List[str]],
    ) -> None:

        super().__init__(*args, **kwargs)
        self._requires_any_args = requires_any_args or set()
        self._requires_all_args = requires_all_args or set()
        self._requires_any_patch = requires_any_patch or set()
        self._requires_all_patch = requires_all_patch or set()
        self._redirect_stdin = redirect_stdin
        self._redirect_stdout = redirect_stdout

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

    def as_plumbum(self, **kwargs: tp.Any) -> 'BoundEnvCommand':
        cmd = super().as_plumbum(**kwargs)

        if self._redirect_stdin:
            cmd = cmd < str(self._redirect_stdin.render(**kwargs))

        if self._redirect_stdout:
            cmd = cmd > str(self._redirect_stdout.render(**kwargs))

        return cmd

    def as_plumbum_wrapped_with(
        self,
        wrapper_cmd: tp.Optional['BoundEnvCommand'] = None,
        adapted_binary_location: tp.Optional[Path] = None,
        **kwargs: tp.Any
    ) -> 'BaseCommand':
        base_cmd = super().as_plumbum(**kwargs)

        # TODO: maybe we should just provide a callable to modify the original
        # command
        if adapted_binary_location:
            if isinstance(base_cmd, LocalCommand):
                base_cmd.executable = base_cmd.executable.copy(
                    adapted_binary_location, override=True
                )
            else:
                base_cmd.cmd.executable = base_cmd.cmd.executable.copy(
                    adapted_binary_location, override=True
                )

        if wrapper_cmd:
            cmd = wrapper_cmd[base_cmd]
        else:
            cmd = base_cmd

        if self._redirect_stdin:
            cmd = cmd < str(self._redirect_stdin.render(**kwargs))

        if self._redirect_stdout:
            cmd = cmd > str(self._redirect_stdout.render(**kwargs))

        return cmd


class VProjectCommand(ProjectCommand):  # type: ignore

    def __init__(self, project: 'VProject', command: Command):
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

        all_args = set(self.v_command.rendered_args(project=self.v_project))
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
