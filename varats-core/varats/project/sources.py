"""Implements additional sources for projects."""

import typing as tp

import benchbuild as bb
import plumbum as pb
from benchbuild.source import Variant, HTTP
from benchbuild.source.base import Revision
from benchbuild.utils.cmd import mkdir, ln, unzip

from varats.paper.paper_config import get_paper_config
from varats.utils.git_util import ShortCommitHash


class FeatureSource(bb.source.FetchableSource):  # type: ignore
    """Feature source that automatically enumerates all configurations."""

    LOCAL_KEY = "config_info"

    def __init__(self) -> None:
        super().__init__(local=self.LOCAL_KEY, remote={"fv_1": "dummy_value"})

    def version(self, target_dir: str, version: str) -> pb.LocalPath:
        return pb.LocalPath('.')

    def versions(self) -> tp.List[Variant]:
        raise NotImplementedError()

    def fetch(self) -> pb.LocalPath:
        raise NotImplementedError()

    @property
    def default(self) -> Variant:
        raise NotImplementedError()

    @property
    def is_expandable(self) -> bool:
        return True

    def is_context_free(self) -> bool:
        return False

    def versions_with_context(self, ctx: Revision) -> tp.Sequence[Variant]:
        """Computes the list of variants for given revision, multiplex with the
        config ids that should be explored.."""
        case_study = get_paper_config().get_case_studies(ctx.project_cls.NAME
                                                        )[0]
        config_ids = case_study.get_config_ids_for_revision(
            ShortCommitHash(ctx.primary.version)
        )

        return [Variant(self, str(config_id)) for config_id in config_ids]


class HTTPUnzip(HTTP):  # type: ignore
    """Fetch and download source via http and auto-unpack using unzip."""

    def version(self, target_dir: str, version: str) -> pb.LocalPath:
        """
        Set up the given version of this HTTPUnzip source.

        This will fetch the given version from the remote source and unpack the
        archive into the build directory using unzip.

        The location matches the behavior of other sources. However, you need
        to consider that benchbuild will return a directory instead of a file path.

        When using workloads, you can refer to a directory with the SourceRootRenderer using
        ``benchbuild.command.source_root``.

        Example:
            You specify a remote version 1.0 of an archive compression.zip and
            a local name of "compression.zip".
            The build directory will look as follows:

            <builddir>/1.0-compression.dir/
            <builddir>/1.0-compression.zip
            <builddir>/compression.zip -> ./1.0-compression.tar.dir

            The content of the archive is found in the directory compression.zip.
            Your workloads need to make sure to reference this directory (e.g. using tokens),
            e.g., ``source_root("compression.zip")``
        """
        archive_path = super().version(target_dir, version)

        target_name = str(pb.local.path(archive_path).with_suffix(".dir"))
        target_path = pb.local.path(target_dir) / target_name
        active_loc = pb.local.path(target_dir) / self.local

        mkdir(target_path)
        unzip(archive_path, "-d", target_path)

        ln('-sf', target_path, active_loc)

        return target_path
