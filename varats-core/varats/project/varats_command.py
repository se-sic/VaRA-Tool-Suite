"""Custom version of benchbuild's Command for use with the VaRA-Tool-Suite."""
import typing as tp

from benchbuild.command import Command

if tp.TYPE_CHECKING:
    import varats.provider.patch.patch_provider as patch_provider


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

    def can_be_executed_by(
        self, extra_args: tp.Set[str],
        applied_patches: 'patch_provider.PatchSet'
    ) -> bool:
        """
        Checks whether this command can be executed with the give configuration.

        Args:
            extra_args: additional command line arguments that will be passed to
                        the command
            applied_patches: patches that were applied to create the executable

        Returns:
            whether this command can be executed
        """
        all_args = set(self._args).union(extra_args)
        all_patch_tags: tp.Set[str] = set()
        for patch in applied_patches:
            if patch.feature_tags:
                all_patch_tags.update(patch.feature_tags)

        return bool((
            not self.requires_any_args or
            all_args.intersection(self.requires_any_args)
        ) and (
            not self.requires_all_args or
            self.requires_all_args.issubset(all_args)
        ) and (
            not self.requires_any_patch or
            all_patch_tags.intersection(self.requires_any_patch)
        ) and (
            not self.requires_all_patch or
            self.requires_all_patch.issubset(all_patch_tags)
        ))
