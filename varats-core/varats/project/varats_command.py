"""Custom version of benchbuild's Command for use with the VaRA-Tool-Suite."""

import typing as tp
from pathlib import Path

from benchbuild.command import ArgsToken, Command, PathToken, ProjectCommand
from plumbum.machines import LocalCommand

from varats.utils.config import get_config_patches

if tp.TYPE_CHECKING:
    from plumbum.commands.base import BaseCommand, BoundEnvCommand

    from varats.project.varats_project import VProject


class PathTokenToArgsRenderer:
    """Renderer making :class:`PathToken` compatible with :class:`ArgsToken`."""

    def __init__(self, path_token: PathToken) -> None:
        """
        Initialize the renderer.

        Args:
            path_token: the path token to wrap
        """
        self._path_token = path_token

    @property
    def unrendered(self) -> str:
        """Placeholder representation of the wrapped token."""
        return str(self._path_token)

    def rendered(self, **kwargs: tp.Any) -> tuple[str, ...]:
        """Render the wrapped path token as a single argument."""
        return (str(self._path_token.render(**kwargs)),)


def make_arg(path_token: PathToken) -> ArgsToken:
    """
    Wraps a :class:`PathToken` to make it compatible with :class:`ArgsToken`.

    Args:
        path_token: the path token to wrap.

    Returns:
        an :class:`ArgsToken` wrapping the given :class:`PathToken`.
    """
    return ArgsToken.make_token(PathTokenToArgsRenderer(path_token))


class VCommand(Command):  # type: ignore [misc]
    """
    Wrapper around benchbuild's :class:`Command` class.

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

    _requires: set[str]

    def __init__(
        self,
        *args: tp.Any,
        requires_any_args: set[str] | None = None,
        requires_all_args: set[str] | None = None,
        forbids_any_args: set[str] | None = None,
        forbids_all_args: set[str] | None = None,
        requires_any_patch: set[str] | None = None,
        requires_all_patch: set[str] | None = None,
        redirect_stdin: PathToken | None = None,
        redirect_stdout: PathToken | None = None,
        **kwargs: str | list[str],
    ) -> None:
        """
        Initialize the command.

        Args:
            args: positional arguments passed to :class:`Command`
            requires_any_args: any of these args must be present
            requires_all_args: all of these args must be present
            forbids_any_args: none of these args may be present
            forbids_all_args: not all of these args may be present at once
            requires_any_patch: any of these patch feature tags must be present
            requires_all_patch: all of these patch feature tags must be present
            redirect_stdin: file to redirect stdin from
            redirect_stdout: file to redirect stdout to
            kwargs: keyword arguments passed to :class:`Command`
        """
        super().__init__(*args, **kwargs)
        self._requires_any_args = requires_any_args or set()
        self._requires_all_args = requires_all_args or set()
        self._forbids_any_args = forbids_any_args or set()
        self._forbids_all_args = forbids_all_args or set()
        self._requires_any_patch = requires_any_patch or set()
        self._requires_all_patch = requires_all_patch or set()
        self._redirect_stdin = redirect_stdin
        self._redirect_stdout = redirect_stdout

    @property
    def requires_any_args(self) -> set[str]:
        """Args of which any must be present."""
        return self._requires_any_args

    @property
    def requires_all_args(self) -> set[str]:
        """Args that must all be present."""
        return self._requires_all_args

    @property
    def forbids_any_args(self) -> set[str]:
        """Args of which none may be present."""
        return self._forbids_any_args

    @property
    def forbids_all_args(self) -> set[str]:
        """Args that may not all be present at once."""
        return self._forbids_all_args

    @property
    def requires_any_patch(self) -> set[str]:
        """Patch feature tags of which any must be present."""
        return self._requires_any_patch

    @property
    def requires_all_patch(self) -> set[str]:
        """Patch feature tags that must all be present."""
        return self._requires_all_patch

    def as_plumbum(self, **kwargs: tp.Any) -> 'BoundEnvCommand':
        """Create a plumbum command with stdin/stdout redirections applied."""
        cmd = super().as_plumbum(**kwargs)

        if self._redirect_stdin:
            cmd = cmd < str(self._redirect_stdin.render(**kwargs))

        if self._redirect_stdout:
            cmd = cmd > str(self._redirect_stdout.render(**kwargs))

        return cmd

    def as_plumbum_wrapped_with(
        self,
        wrapper_cmd: tp.Optional['BoundEnvCommand'] = None,
        adapted_binary_location: Path | None = None,
        **kwargs: tp.Any,
    ) -> 'BaseCommand':
        """
        Create a plumbum command, optionally wrapped by another command.

        Args:
            wrapper_cmd: command to wrap this command with
            adapted_binary_location: replacement location for the executable
            kwargs: arguments used for rendering the command

        Returns:
            the (wrapped) plumbum command with redirections applied
        """
        base_cmd = super().as_plumbum(**kwargs)

        # TODO: maybe we should just provide a callable to modify the original  # ruff: ignore[line-contains-todo]
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

        cmd = wrapper_cmd[base_cmd.formulate()] if wrapper_cmd else base_cmd

        if self._redirect_stdin:
            cmd = cmd < str(self._redirect_stdin.render(**kwargs))

        if self._redirect_stdout:
            cmd = cmd > str(self._redirect_stdout.render(**kwargs))

        return cmd


class VProjectCommand(ProjectCommand):  # type: ignore
    """:class:`ProjectCommand` that can filter commands by configuration."""

    def __init__(self, project: 'VProject', command: Command) -> None:
        """
        Initialize the project command.

        Args:
            project: the project the command belongs to
            command: the command to wrap
        """
        super().__init__(project, command)
        self.v_command = command if isinstance(command, VCommand) else None
        self.v_project = project

    def can_be_executed(self) -> bool:
        """
        Checks whether this command can be executed with the configuration.

        Returns:
            whether this command can be executed
        """
        # non-VCommands do not support filtering by configuration, so we default
        # to using them as-is
        if self.v_command is None:
            return True

        all_args = set(self.v_command.rendered_args(project=self.v_project))
        all_patch_tags: set[str] = set()

        for patch in get_config_patches(self.v_project):
            if patch.feature_tags:
                all_patch_tags.update(patch.feature_tags)

        return bool(
            (
                not self.v_command.requires_any_args
                or all_args.intersection(self.v_command.requires_any_args)
            )
            and (
                not self.v_command.requires_all_args
                or self.v_command.requires_all_args.issubset(all_args)
            )
            and (
                not self.v_command.forbids_any_args
                or all_args.isdisjoint(self.v_command.forbids_any_args)
            )
            and (
                not self.v_command.forbids_all_args
                or not self.v_command.forbids_all_args.issubset(all_args)
            )
            and (
                not self.v_command.requires_any_patch
                or all_patch_tags.intersection(
                    self.v_command.requires_any_patch
                )
            )
            and (
                not self.v_command.requires_all_patch
                or self.v_command.requires_all_patch.issubset(all_patch_tags)
            )
        )
